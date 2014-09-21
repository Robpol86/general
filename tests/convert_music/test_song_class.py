import json
import os

from mutagen.flac import FLAC, Picture
from mutagen.id3 import COMM, ID3
import pytest

from convert_music import OPTIONS, PAD_COMMENT, Song


def test_instantiation():
    flac_dir = '/tmp/flac_dir'
    mp3_dir = '/tmp/mp3_dir'

    song = Song('/tmp/flac_dir/A - 2000 - T - 0 - S.flac', flac_dir, mp3_dir)
    assert 'A - 2000 - T - 0 - S.flac' == song.flac_name
    assert '/tmp/mp3_dir/A - 2000 - T - 0 - S.mp3' == song.mp3_path
    assert 'A' == song.filename_artist
    assert '2000' == song.filename_date
    assert 'T' == song.filename_album
    assert '0' == song.filename_track
    assert 'S' == song.filename_title

    song = Song('/tmp/flac_dir/subdir/A - 2000 - T - 0 - S.flac', flac_dir, mp3_dir)
    assert 'A - 2000 - T - 0 - S.flac' == song.flac_name
    assert '/tmp/mp3_dir/subdir/A - 2000 - T - 0 - S.mp3' == song.mp3_path


def test_invalid_filename():
    flac_dir = '/tmp/flac_dir'
    mp3_dir = '/tmp/mp3_dir'

    with pytest.raises(ValueError):
        Song('/tmp/flac_dir/A - 2000 - T - 0 - S', flac_dir, mp3_dir)

    with pytest.raises(ValueError):
        Song('/tmp/flac_dir/A - 2000 - T - S.flac', flac_dir, mp3_dir)

    with pytest.raises(ValueError):
        Song('/tmp/flac_dir/A - 2000 - T - - S.flac', flac_dir, mp3_dir)

    Song('/tmp/flac_dir/A - 2000 - T - 0 - S.flac', flac_dir, mp3_dir)


def test_properties():
    flac_dir = '/tmp/flac_dir'
    mp3_dir = '/tmp/mp3_dir'
    song = Song('/tmp/flac_dir/Artist - 2000 - Album - 01 - Title.flac', flac_dir, mp3_dir)

    song.flac_artist = 'artist'
    assert song.bad_artist
    song.flac_artist = 'Artist'
    assert not song.bad_artist

    song.flac_date = 2000
    assert song.bad_date
    song.flac_date = '200'
    assert song.bad_date
    song.flac_date = '2000'
    assert not song.bad_date

    song.filename_date = '200'
    song.flac_date = '200'
    assert song.bad_date
    song.filename_date = '20000'
    song.flac_date = '20000'
    assert song.bad_date
    song.filename_date = '200a'
    song.flac_date = '200a'
    assert song.bad_date
    song.filename_date = '2000.1'
    song.flac_date = '2000.1'
    assert song.bad_date
    song.filename_date = '2000'
    song.flac_date = '2000'
    assert not song.bad_date

    song.flac_album = 'album'
    assert song.bad_album
    song.flac_album = 'Album'
    assert not song.bad_album
    song.filename_album = 'Album (Disc 1)'
    assert song.bad_album
    song.flac_disc = '1'
    assert not song.bad_album

    song.flac_track = 1
    assert song.bad_track
    song.flac_track = '1'
    assert song.bad_track
    song.flac_track = '01'
    assert not song.bad_track

    song.filename_track = '1'
    song.flac_track = '1'
    assert song.bad_track
    song.filename_track = '0001'
    song.flac_track = '0001'
    assert song.bad_track
    song.filename_track = 'a1'
    song.flac_track = 'a1'
    assert song.bad_track
    song.filename_track = '.1'
    song.flac_track = '.1'
    assert song.bad_track
    song.filename_track = '001'
    song.flac_track = '001'
    assert not song.bad_track

    song.flac_title = 'title'
    assert song.bad_title
    song.flac_title = 'Title'
    assert not song.bad_title

    OPTIONS['--ignore-lyrics'] = True
    assert not song.bad_lyrics
    OPTIONS['--ignore-lyrics'] = False
    assert song.bad_lyrics
    song.flac_has_lyrics = True
    assert not song.bad_lyrics

    OPTIONS['--ignore-art'] = True
    assert not song.bad_picture
    OPTIONS['--ignore-art'] = False
    assert song.bad_picture
    song.flac_has_picture = True
    assert not song.bad_picture

    assert song.metadata_ok
    song.flac_has_picture = False
    assert not song.metadata_ok

    song.flac_current_mtime = 0
    song.flac_current_size = 0
    song.mp3_current_mtime = 0
    song.mp3_current_size = 0
    assert not song.skip_conversion
    song.flac_stored_mtime = 0
    song.flac_stored_size = 0
    song.mp3_stored_mtime = 0
    song.mp3_stored_size = 0
    assert song.skip_conversion


@pytest.mark.parametrize('invalid_data', [False, True])
def test_get_metadata_no_tags_invalid_data(tmpdir, invalid_data):
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')

    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    if invalid_data:
        flac.write('\0', 'wb')
        mp3.write('\0', 'wb')
    else:
        with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
            flac.write(f.read(), 'wb')
        with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
            mp3.write(f.read(), 'wb')

    song = Song(str(flac), str(flac_dir), str(mp3_dir))
    song.get_metadata()

    assert 1411333042 < song.flac_current_mtime
    assert 1411333042 < song.mp3_current_mtime
    if invalid_data:
        assert 1 == song.flac_current_size
        assert 1 == song.mp3_current_size
    else:
        assert 1000 < song.flac_current_size
        assert 1000 < song.mp3_current_size

    assert ['', '', '', '', ''] == [song.flac_artist, song.flac_date, song.flac_album, song.flac_track, song.flac_title]
    assert [False, False] == [song.flac_has_lyrics, song.flac_has_picture]

    assert all([song.bad_artist, song.bad_date, song.bad_album, song.bad_track, song.bad_title])
    assert all([song.bad_lyrics, song.bad_picture])
    assert not song.metadata_ok
    assert not song.skip_conversion


def test_get_metadata(tmpdir):
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = '/tmp/mp3_dir'
    flac = flac_dir.join('Artist - 2001 - Album (Disc 1) - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')

    tags = FLAC(str(flac))
    tags.update(dict(artist='Artist', date='2001', album='Album', discnumber='1', tracknumber='01', title='Title',
                     unsyncedlyrics='L'))
    image = Picture()
    image.type, image.mime = 3, 'image/jpeg'
    with open(os.path.join(os.path.dirname(__file__), '1_album_art.jpg'), 'rb') as f:
        image.data = f.read()
    tags.add_picture(image)
    tags.save()
    song = Song(str(flac), str(flac_dir), mp3_dir)
    song.get_metadata()

    assert dict() == OPTIONS
    assert ['Artist', '2001', 'Album'] == [song.flac_artist, song.flac_date, song.flac_album]
    assert ['01', 'Title'] == [song.flac_track, song.flac_title]
    assert [True, True] == [song.flac_has_lyrics, song.flac_has_picture]
    assert song.metadata_ok


def test_skip_conversion(tmpdir):
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    flac = flac_dir.join('Artist - 2001 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')

    tags = FLAC(str(flac))
    tags.update(dict(artist='Artist', date='2001', album='Album', tracknumber='01', title='Title'))
    tags.save()
    song = Song(str(flac), str(flac_dir), str(mp3_dir))
    song.get_metadata()
    OPTIONS['--ignore-lyrics'] = True
    OPTIONS['--ignore-art'] = True
    
    assert song.metadata_ok
    assert not song.skip_conversion
    
    mp3 = mp3_dir.join('Artist - 2001 - Album - 01 - Title.mp3').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    id3 = ID3(str(mp3))
    id3.delete()
    id3.add(COMM(encoding=3, lang='eng', desc='', text=(' ' * PAD_COMMENT)))
    id3.save(v1=2)
    comment = json.dumps(dict(
        flac_mtime=int(flac.mtime()), flac_size=int(flac.size()), mp3_mtime=int(mp3.mtime()), mp3_size=int(mp3.size())
    ))
    id3.add(COMM(encoding=3, lang='eng', desc='', text=comment))  # Now put in real data.
    id3.save(v1=2)

    song = Song(str(flac), str(flac_dir), str(mp3_dir))
    song.get_metadata()

    assert song.metadata_ok
    assert song.skip_conversion
