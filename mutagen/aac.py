# -*- coding: utf-8 -*-
# Copyright (C) 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""
ADTS - Audio Data Transport Stream (AAC streaming format)
See ISO/IEC 13818-7

TODO: ADIF
"""

from mutagen import StreamInfo
from mutagen._file import FileType
from mutagen._util import BitReader, BitReaderError, MutagenError
from mutagen._compat import endswith, xrange


class _ADTSStream(object):
    """Represents a series of frames belonging to the same stream"""

    parsed_frames = 0
    """Number of successfully parsed frames"""

    offset = 0
    """offset in bytes at which the stream starts (the first sync word)"""

    @classmethod
    def find_stream(cls, fileobj, max_bytes):
        """Returns a possibly valid _ADTSStream or None.

        Args:
            max_bytes (int): maximum bytes to read
        """

        r = BitReader(fileobj)
        stream = cls(r)
        if stream.sync(max_bytes):
            stream.offset = (r.get_position() - 12) // 8
            return stream

    _FREQS = [
        96000, 88200, 64000, 48000,
        44100, 32000, 24000, 22050,
        16000, 12000, 11025, 8000,
        7350,
    ]

    def sync(self, max_bytes):
        """Find the next sync.
        Returns True if found."""

        # at least 2 bytes for the sync
        max_bytes = max(max_bytes, 2)

        r = self._r
        r.align()
        while max_bytes > 0:
            try:
                b = r.bytes(1)
                if b == b"\xff":
                    if r.bits(4) == 0xf:
                        return True
                    r.align()
                    max_bytes -= 2
                else:
                    max_bytes -= 1
            except BitReaderError:
                return False
        return False

    def __init__(self, r):
        """Use _ADTSStream.find_stream to create a stream"""

        self._fixed_header_key = None
        self._r = r
        self.offset = -1
        self.parsed_frames = 0

        self._samples = 0
        self._payload = 0
        self._start = r.get_position() / 8
        self._last = self._start

    @property
    def bitrate(self):
        """Bitrate of the raw aac blocks, excluding framing/crc"""

        assert self.parsed_frames, "no frame parsed yet"

        if self._samples == 0:
            return 0

        return (8 * self._payload * self.frequency) / self._samples

    @property
    def samples(self):
        """samples so far"""

        assert self.parsed_frames, "no frame parsed yet"

        return self._samples

    @property
    def size(self):
        """bytes read in the stream so far (including framing)"""

        assert self.parsed_frames, "no frame parsed yet"

        return self._last - self._start

    @property
    def channels(self):
        """0 means unknown"""

        assert self.parsed_frames, "no frame parsed yet"

        b_index = self._fixed_header_key[6]
        if b_index == 7:
            return 8
        elif b_index > 7:
            return 0
        else:
            return b_index

    @property
    def frequency(self):
        """0 means unknown"""

        assert self.parsed_frames, "no frame parsed yet"

        f_index = self._fixed_header_key[4]
        try:
            return self._FREQS[f_index]
        except IndexError:
            return 0

    def parse_frame(self):
        """True if parsing was successful.
        Fails either because the frame wasn't valid or the stream ended.
        """

        try:
            return self._parse_frame()
        except BitReaderError:
            return False

    def _parse_frame(self):
        r = self._r
        # start == position of sync word
        start = r.get_position() - 12

        # adts_fixed_header
        id_ = r.bits(1)
        layer = r.bits(2)
        protection_absent = r.bits(1)

        profile = r.bits(2)
        sampling_frequency_index = r.bits(4)
        private_bit = r.bits(1)
        # TODO: if 0 we could parse program_config_element()
        channel_configuration = r.bits(3)
        original_copy = r.bits(1)
        home = r.bits(1)

        # the fixed header has to be the same for every frame in the stream
        fixed_header_key = (
            id_, layer, protection_absent, profile, sampling_frequency_index,
            private_bit, channel_configuration, original_copy, home,
        )

        if self._fixed_header_key is None:
            self._fixed_header_key = fixed_header_key
        else:
            if self._fixed_header_key != fixed_header_key:
                return False

        # adts_variable_header
        r.skip(2)  # copyright_identification_bit/start
        frame_length = r.bits(13)
        r.skip(11)  # adts_buffer_fullness
        nordbif = r.bits(2)
        # adts_variable_header end

        crc_overhead = 0
        if not protection_absent:
            crc_overhead += (nordbif + 1) * 16
            if nordbif != 0:
                crc_overhead *= 2

        left = (frame_length * 8) - (r.get_position() - start)
        if left < 0:
            return False
        r.skip(left)
        assert r.is_aligned()

        self._payload += (left - crc_overhead) / 8
        self._samples += (nordbif + 1) * 1024
        self._last = r.get_position() / 8

        self.parsed_frames += 1
        return True


class AACError(MutagenError):
    pass


class AACInfo(StreamInfo):
    """AAC stream information.

    Attributes:

    * channels -- number of audio channels
    * length -- file length in seconds, as a float
    * sample_rate -- audio sampling rate in Hz
    * bitrate -- audio bitrate, in bits per second

    Both bitrate and length are an approximation based on the first few
    frames in the stream.
    """

    channels = 0
    length = 0
    sample_rate = 0
    bitrate = 0

    def __init__(self, fileobj):
        max_initial_read = 512
        max_resync_read = 10
        max_sync_tries = 10

        frames_max = 100
        frames_needed = 3

        # skip id3v2 header
        start_offset = 0
        header = fileobj.read(10)
        from mutagen.id3 import BitPaddedInt
        if header.startswith(b"ID3"):
            size = BitPaddedInt(header[6:])
            start_offset = size + 10

        # Try up to X times to find a sync word and read up to Y frames.
        # If more than Z frames are valid we assume a valid stream
        offset = start_offset
        for i in xrange(max_sync_tries):
            fileobj.seek(offset)
            s = _ADTSStream.find_stream(fileobj, max_initial_read)
            if s is None:
                raise AACError("sync not found")
            # start right after the last found offset
            offset += s.offset + 1

            for i in xrange(frames_max):
                if not s.parse_frame():
                    break
                if not s.sync(max_resync_read):
                    break

            if s.parsed_frames >= frames_needed:
                break
        else:
            raise AACError(
                "no valid stream found (only %d frames)" % s.parsed_frames)

        self.sample_rate = s.frequency
        self.channels = s.channels
        self.bitrate = s.bitrate

        # size from stream start to end of file
        fileobj.seek(0, 2)
        stream_size = fileobj.tell() - (offset + s.offset)
        # approx
        self.length = float(s.samples * stream_size) / (s.size * s.frequency)

    def pprint(self):
        return "AAC (ADTS), %d Hz, ~%.2f seconds, %d channel(s), ~%d bps" % (
            self.sample_rate, self.length, self.channels, self.bitrate)


class AAC(FileType):

    _mimes = ["audio/x-aac"]

    def load(self, filename):
        self.filename = filename
        with open(filename, "rb") as h:
            self.info = AACInfo(h)

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()
        return endswith(filename, ".aac") or endswith(filename, ".adts")


Open = AAC
error = AACError

__all__ = ["AAC", "Open"]
