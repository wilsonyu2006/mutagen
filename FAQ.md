# Specifications #

## Does Mutagen support writing ID3v2.3 (or v2.2)? ##

No. This is an intentional decision to make it as easy as possible to ensure Mutagen conforms to the ID3v2.4 specification. Mutagen will read ID3v2.3 and v2.2 considerably better than most libraries, but cannot write them.

## Can Mutagen write Shift-JIS / KOI-8 / Big-5? ##

No. Mutagen is capable of handling Chinese, Russian, and Japanese characters, provided they are encoded correctly. ID3v2.4 supports the UTF-8 and UTF-16 encodings of Unicode; most other formats support only UTF-8. To write a different character encoding would violate the format specifications.

# Programming Interface #

## ID3("foo.mp3") raises mutagen.id3.ID3NoHeaderError - How do I add an ID3 tag? ##

You should open MP3s as MP3s, not as a particular (possibly missing) tag format:
```
audio = mutagen.mp3.MP3("foo.mp3")
audio["TIT2"] = TIT2(encoding=3, text=["Title"])
```

The ID3 tag will be automatically created if you set any frames.

If you need to add a tag to a file that doesn't exist or that isn't an audio format supported by Mutagen, you can either construct a file-less ID3 tag and save it to that file:
```
tags = ID3()
tags.add(TIT2(encoding=3, text=["Some Title"]))
...
tags.save("foo.id3")
```

## How do I fix incorrect character encodings? ##

If you have some text frame that Mutagen interpreted as ISO-8859-1, but it was actually some out-of-spec encoding like KOI8-R, you can use:
```
frame.text = unicode(frame).encode("iso-8859-1").decode("koi8-r")
```