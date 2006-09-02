
import shutil, os
from tests import TestCase, add
from mutagen.flac import to_int_be, Padding, VCFLACDict, MetadataBlock
from mutagen.flac import StreamInfo, SeekTable, CueSheet, FLAC, delete
from tests.test__vorbis import TVCommentDict, VComment

class Tto_int_be(TestCase):
    uses_mmap = False

    def test_empty(self): self.failUnlessEqual(to_int_be(""), 0)
    def test_0(self): self.failUnlessEqual(to_int_be("\x00"), 0)
    def test_1(self): self.failUnlessEqual(to_int_be("\x01"), 1)
    def test_256(self): self.failUnlessEqual(to_int_be("\x01\x00"), 256)
    def test_long(self):
        self.failUnlessEqual(to_int_be("\x01\x00\x00\x00\x00"), 2**32)
add(Tto_int_be)

class TVCFLACDict(TVCommentDict):
    uses_mmap = False

    Kind = VCFLACDict

    def test_roundtrip_vc(self):
        self.failUnlessEqual(self.c, VComment(self.c.write() + "\x01"))
add(TVCFLACDict)

class TMetadataBlock(TestCase):
    uses_mmap = False

    def test_empty(self):
        self.failUnlessEqual(MetadataBlock("").write(), "")
    def test_not_empty(self):
        self.failUnlessEqual(MetadataBlock("foobar").write(), "foobar")

    def test_change(self):
        b = MetadataBlock("foobar")
        b.data = "quux"
        self.failUnlessEqual(b.write(), "quux")

    def test_writeblocks(self):
        blocks = [Padding("\x00" * 20), Padding("\x00" * 30)]
        self.failUnlessEqual(len(MetadataBlock.writeblocks(blocks)), 58)

    def test_ctr_garbage(self):
        self.failUnlessRaises(TypeError, StreamInfo, 12)

    def test_group_padding(self):
        blocks = [Padding("\x00" * 20), Padding("\x00" * 30),
                  MetadataBlock("foobar")]
        blocks[-1].code = 0
        length1 = len(MetadataBlock.writeblocks(blocks))
        MetadataBlock.group_padding(blocks)
        length2 = len(MetadataBlock.writeblocks(blocks))
        self.failUnlessEqual(length1, length2)
        self.failUnlessEqual(len(blocks), 2)
add(TMetadataBlock)

class TStreamInfo(TestCase):
    uses_mmap = False

    data = ("\x12\x00\x12\x00\x00\x00\x0e\x00\x35\xea\x0a\xc4\x42\xf0"
            "\x00\xca\x30\x14\x28\x90\xf9\xe1\x29\x32\x13\x01\xd4\xa7"
            "\xa9\x11\x21\x38\xab\x91")
    def setUp(self):
        self.i = StreamInfo(self.data)

    def test_blocksize(self):
        self.failUnlessEqual(self.i.max_blocksize, 4608)
        self.failUnlessEqual(self.i.min_blocksize, 4608)
        self.failUnless(self.i.min_blocksize <= self.i.max_blocksize)
    def test_framesize(self):
        self.failUnlessEqual(self.i.min_framesize, 14)
        self.failUnlessEqual(self.i.max_framesize, 13802)
        self.failUnless(self.i.min_framesize <= self.i.max_framesize)
    def test_sample_rate(self): self.failUnlessEqual(self.i.sample_rate, 44100)
    def test_channels(self): self.failUnlessEqual(self.i.channels, 2)
    def test_bps(self): self.failUnlessEqual(self.i.bits_per_sample, 16)
    def test_length(self): self.failUnlessAlmostEqual(self.i.length, 300.5, 1)
    def test_total_samples(self):
        self.failUnlessEqual(self.i.total_samples, 13250580)
    def test_md5_signature(self):
        self.failUnlessEqual(self.i.md5_signature,
                             int("2890f9e129321301d4a7a9112138ab91", 16))
    def test_eq(self): self.failUnlessEqual(self.i, self.i)
    def test_roundtrip(self):
        self.failUnlessEqual(StreamInfo(self.i.write()), self.i)
add(TStreamInfo)
        
class TSeekTable(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    uses_mmap = False

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.st = self.flac.seektable
    def test_seektable(self):
        self.failUnlessEqual(self.st.seekpoints,
                             [(0, 0, 4608),
                              (41472, 11852, 4608),
                              (50688, 14484, 4608),
                              (87552, 25022, 4608),
                              (105984, 30284, 4608),
                              (0xFFFFFFFFFFFFFFFF, 0, 0)])
    def test_eq(self): self.failUnlessEqual(self.st, self.st)
    def test_neq(self): self.failIfEqual(self.st, 12)
    def test_repr(self): repr(self.st)
    def test_roundtrip(self):
        self.failUnlessEqual(SeekTable(self.st.write()), self.st)
add(TSeekTable)

class TCueSheet(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    uses_mmap = False

    def setUp(self):
        self.flac = FLAC(self.SAMPLE)
        self.cs = self.flac.cuesheet
    def test_cuesheet(self):
        self.failUnlessEqual(self.cs.media_catalog_number, "1234567890123")
        self.failUnlessEqual(self.cs.lead_in_samples, 88200)
        self.failUnlessEqual(self.cs.compact_disc, True)
        self.failUnlessEqual(len(self.cs.tracks), 4)
    def test_first_track(self):
        self.failUnlessEqual(self.cs.tracks[0].track_number, 1)
        self.failUnlessEqual(self.cs.tracks[0].start_offset, 0)
        self.failUnlessEqual(self.cs.tracks[0].isrc, '123456789012')
        self.failUnlessEqual(self.cs.tracks[0].type, 0)
        self.failUnlessEqual(self.cs.tracks[0].pre_emphasis, False)
        self.failUnlessEqual(self.cs.tracks[0].indexes, [(1, 0)])
    def test_second_track(self):
        self.failUnlessEqual(self.cs.tracks[1].track_number, 2)
        self.failUnlessEqual(self.cs.tracks[1].start_offset, 44100L)
        self.failUnlessEqual(self.cs.tracks[1].isrc, '')
        self.failUnlessEqual(self.cs.tracks[1].type, 1)
        self.failUnlessEqual(self.cs.tracks[1].pre_emphasis, True)
        self.failUnlessEqual(self.cs.tracks[1].indexes, [(1, 0),
                                                         (2, 588)])
    def test_lead_out(self):
        self.failUnlessEqual(self.cs.tracks[-1].track_number, 170)
        self.failUnlessEqual(self.cs.tracks[-1].start_offset, 162496)
        self.failUnlessEqual(self.cs.tracks[-1].isrc, '')
        self.failUnlessEqual(self.cs.tracks[-1].type, 0)
        self.failUnlessEqual(self.cs.tracks[-1].pre_emphasis, False)
        self.failUnlessEqual(self.cs.tracks[-1].indexes, [])
    def test_eq(self): self.failUnlessEqual(self.cs, self.cs)
    def test_neq(self): self.failIfEqual(self.cs, 12)
    def test_repr(self): repr(self.cs)
    def test_roundtrip(self):
        self.failUnlessEqual(CueSheet(self.cs.write()), self.cs)
add(TCueSheet)

class TPadding(TestCase):
    uses_mmap = False

    def setUp(self): self.b = Padding("\x00" * 100)
    def test_padding(self): self.failUnlessEqual(self.b.write(), "\x00" * 100)
    def test_blank(self): self.failIf(Padding().write())
    def test_empty(self): self.failIf(Padding("").write())
    def test_repr(self): repr(Padding())
    def test_change(self):
        self.b.length = 20
        self.failUnlessEqual(self.b.write(), "\x00" * 20)
add(TPadding)

class TFLAC(TestCase):
    SAMPLE = os.path.join("tests", "data", "silence-44-s.flac")
    NEW = SAMPLE + ".new"
    def setUp(self):
        shutil.copy(self.SAMPLE, self.NEW)
        self.failUnlessEqual(file(self.SAMPLE).read(), file(self.NEW).read())
        self.flac = FLAC(self.NEW)

    def test_delete(self):
        self.failUnless(self.flac.tags)
        self.flac.delete()
        self.failIf(self.flac.tags)
        flac = FLAC(self.NEW)
        self.failIf(flac.tags)

    def test_module_delete(self):
        delete(self.NEW)
        flac = FLAC(self.NEW)
        self.failIf(flac.tags)

    def test_info(self):
        self.failUnlessAlmostEqual(FLAC(self.NEW).info.length, 3.7, 1)

    def test_keys(self):
        self.failUnlessEqual(self.flac.keys(), self.flac.tags.keys())

    def test_values(self):
        self.failUnlessEqual(self.flac.values(), self.flac.tags.values())

    def test_items(self):
        self.failUnlessEqual(self.flac.items(), self.flac.tags.items())

    def test_vc(self):
        self.failUnlessEqual(self.flac['title'][0], 'Silence')

    def test_write_nochange(self):
        f = FLAC(self.NEW)
        f.save()
        self.failUnlessEqual(file(self.SAMPLE).read(), file(self.NEW).read())

    def test_write_changetitle(self):
        f = FLAC(self.NEW)
        f["title"] = "A New Title"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["title"][0], "A New Title")

    def test_force_grow(self):
        f = FLAC(self.NEW)
        f["faketag"] = ["a" * 1000] * 1000
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["faketag"], ["a" * 1000] * 1000)

    def test_force_shrink(self):
        self.test_force_grow()
        f = FLAC(self.NEW)
        f["faketag"] = "foo"
        f.save()
        f = FLAC(self.NEW)
        self.failUnlessEqual(f["faketag"], ["foo"])

    def test_add_vc(self):
        f = FLAC(os.path.join("tests", "data", "no-tags.flac"))
        self.failIf(f.tags)
        f.add_tags()
        self.failUnless(f.tags == [])
        self.failUnlessRaises(ValueError, f.add_tags)

    def test_add_vc_implicit(self):
        f = FLAC(os.path.join("tests", "data", "no-tags.flac"))
        self.failIf(f.tags)
        f["foo"] = "bar"
        self.failUnless(f.tags == [("foo", "bar")])
        self.failUnlessRaises(ValueError, f.add_tags)

    def test_with_real_flac(self):
        self.flac["faketag"] = "foobar" * 1000
        self.flac.save()
        badval = os.system("tools/notarealprogram 2> /dev/null")
        value = os.system("flac -t %s 2> /dev/null" % self.flac.filename)
        self.failIf(value and value != badval)

    def test_save_unknown_block(self):
        block = MetadataBlock("test block data")
        block.code = 99
        self.flac.metadata_blocks.append(block)
        self.flac.save()

    def test_load_unknown_block(self):
        self.test_save_unknown_block()
        flac = FLAC(self.NEW)
        self.failUnlessEqual(len(flac.metadata_blocks), 6)
        self.failUnlessEqual(flac.metadata_blocks[4].code, 99)
        self.failUnlessEqual(flac.metadata_blocks[4].data, "test block data")

    def test_two_vorbis_blocks(self):
        self.flac.metadata_blocks.append(self.flac.metadata_blocks[1])
        self.flac.save()
        self.failUnlessRaises(IOError, FLAC, self.NEW)

    def test_missing_streaminfo(self):
        self.flac.metadata_blocks.pop(0)
        self.flac.save()
        self.failUnlessRaises(IOError, FLAC, self.NEW)

    def test_load_invalid_flac(self):
        self.failUnlessRaises(
            IOError, FLAC, os.path.join("tests", "data", "xing.mp3"))

    def test_save_invalid_flac(self):
        self.failUnlessRaises(
            IOError, self.flac.save, os.path.join("tests", "data", "xing.mp3"))

    def test_pprint(self):
        self.failUnless(self.flac.pprint())

    def test_double_load(self):
        blocks = list(self.flac.metadata_blocks)
        self.flac.load(self.flac.filename)
        self.failUnlessEqual(blocks, self.flac.metadata_blocks)

    def test_seektable(self):
        self.failUnless(self.flac.seektable)

    def test_cuesheet(self):
        self.failUnless(self.flac.cuesheet)

    def tearDown(self):
        os.unlink(self.NEW)

add(TFLAC)

NOTFOUND = os.system("tools/notarealprogram 2> /dev/null")

if os.system("flac 2> /dev/null > /dev/null") == NOTFOUND:
    print "WARNING: Skipping FLAC reference tests."
