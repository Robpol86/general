import os
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from convert_music import ConvertFiles, find_files


def test_write_tags(tmpdir):
    """Test writing tags from a FLAC to mp3 file."""
    # Prepare.
    flac = tmpdir.mkdir('flac').join('song.flac').ensure(file=True)
    mp3 = tmpdir.mkdir('mp3').join('song.mp3').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    flac, mp3 = str(flac.realpath()), str(mp3.realpath())
    tags = FLAC(flac)
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01', title='Title', unsyncedlyrics='L'))
    image = Picture()
    image.type, image.mime = 3, 'image/jpeg'
    with open(os.path.join(os.path.dirname(__file__), '1_album_art.jpg'), 'rb') as f:
        image.data = f.read()
    tags.add_picture(image)
    tags.save()
    # Test.
    ConvertFiles.write_tags(flac, mp3)
    # Check.
    id3 = ID3(mp3)
    assert 'Artist2' == id3['TPE1']
    assert '2012' == id3['TDRC']
    assert 'Album' == id3['TALB']
    assert '01' == id3['TRCK']
    assert 'Title' == id3['TIT2']
    assert 'L' == id3["USLT:Lyrics:'eng'"].text
    with open(os.path.join(os.path.dirname(__file__), '1_album_art.jpg'), 'rb') as f:
        assert f.read() == id3['APIC:'].data
    assert ({}, [], [], []) == find_files(str(tmpdir.join('flac')), str(tmpdir.join('mp3')))
