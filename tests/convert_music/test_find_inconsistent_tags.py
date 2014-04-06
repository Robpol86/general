import os
from mutagen.flac import FLAC, Picture
from convert_music import find_inconsistent_tags


def test_invalid_filename(tmpdir):
    """Test when the FLAC filename is invalid."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - Album - 01 - Title.flac').ensure(file=True)
    a_messages = find_inconsistent_tags([str(flac.realpath())])
    e_messages = {str(flac.realpath()): ["Filename doesn't have five items."]}
    assert e_messages == a_messages


def test_invalid_file(tmpdir):
    """Test when FLAC file isn't really a FLAC file."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    a_messages = find_inconsistent_tags([str(flac.realpath())])
    e_messages = {str(flac.realpath()): ["Invalid file."]}
    assert e_messages == a_messages


def test_no_tags(tmpdir):
    """Test FLAC file with no tags."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    a_messages = find_inconsistent_tags([str(flac.realpath())])
    e_messages = {str(flac.realpath()): [
        "Artist mismatch: Artist2 != ",
        "Album mismatch: Album != ",
        "Title mismatch: Title != ",
        "Date mismatch: 2012 != ",
        "Track number mismatch: 01 != ",
        "No album art.",
        "No lyrics."
    ]}
    assert e_messages == a_messages


def test_basic_tags(tmpdir):
    """Test when artist, album, title are the only valid tags."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', album='Album', title='Title'))
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())])
    e_messages = {str(flac.realpath()): [
        "Date mismatch: 2012 != ",
        "Track number mismatch: 01 != ",
        "No album art.",
        "No lyrics."
    ]}
    assert e_messages == a_messages


def test_basic_numeric_tags(tmpdir):
    """Test when everything but lyrics/art are valid."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01', title='Title'))
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())])
    e_messages = {str(flac.realpath()): [
        "No album art.",
        "No lyrics."
    ]}
    assert e_messages == a_messages


def test_basic_numeric_tags_ignore_lyrics_art(tmpdir):
    """Test when everything but lyrics/art are valid, while ignoring lyrics/art."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01', title='Title'))
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())], True, True)
    assert {} == a_messages


def test_art_lyrics(tmpdir):
    """Test when everything is valid."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01', title='Title', unsyncedlyrics='L'))
    image = Picture()
    image.type, image.mime = 3, 'image/jpeg'
    with open(os.path.join(os.path.dirname(__file__), '1_album_art.jpg'), 'rb') as f:
        image.data = f.read()
    tags.add_picture(image)
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())], False, False)
    assert {} == a_messages


def test_tag_alpha_instead_of_numeric(tmpdir):
    """Test when track number and date tags aren't integers."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012 ', album='Album', tracknumber='01 ', title='Title'))
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())], True, True)
    e_messages = {str(flac.realpath()): [
        "Date mismatch: 2012 != 2012 ",
        "Track number mismatch: 01 != 01 "
    ]}
    assert e_messages == a_messages


def test_file_name_alpha_instead_of_numeric(tmpdir):
    """Test when track number and date file names aren't integers."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 2012  - Album - 0.1 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01 ', title='Title'))
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())], True, True)
    e_messages = {str(flac.realpath()): [
        "Filename date not a number.",
        "Filename track number not a number."
    ]}
    assert e_messages == a_messages


def test_single_digit(tmpdir):
    """Test for single digit track numbers (should be 2) and dates (should be 4)."""
    flac_dir = tmpdir.mkdir('flac')
    flac = flac_dir.join('Artist2 - 1 - Album - 1 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='1', album='Album', tracknumber='1', title='Title'))
    tags.save()
    a_messages = find_inconsistent_tags([str(flac.realpath())], True, True)
    e_messages = {str(flac.realpath()): [
        "Filename date not four digits.",
        "Filename track number not two digits."
    ]}
    assert e_messages == a_messages


def test_one_valid_two_invalid(tmpdir):
    """Test when one FLAC file is fully valid and another one isn't."""
    flac_dir = tmpdir.mkdir('flac')
    flac_files = []
    # Valid.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01', title='Title'))
    tags.save()
    flac_files.append(str(flac.realpath()))
    # Invalid.
    flac = flac_dir.join('Artist - 2014 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2014', album='Album', tracknumber='01', title='Title'))
    tags.save()
    flac_files.append(str(flac.realpath()))
    # Test.
    a_messages = find_inconsistent_tags(flac_files, True, True)
    e_messages = {flac_files[1]: [
        "Artist mismatch: Artist != Artist2",
    ]}
    assert e_messages == a_messages


def test_two_invalid(tmpdir):
    """Test when two FLAC files have invalid tags."""
    flac_dir = tmpdir.mkdir('flac')
    flac_files = []
    # One.
    flac = flac_dir.join('Artist2 - 202 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2012', album='Album', tracknumber='01', title='Title'))
    tags.save()
    flac_files.append(str(flac.realpath()))
    # Two.
    flac = flac_dir.join('Artist - 2014 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    tags = FLAC(str(flac.realpath()))
    tags.update(dict(artist='Artist2', date='2014', album='Album', tracknumber='01', title='Title'))
    tags.save()
    flac_files.append(str(flac.realpath()))
    # Test.
    a_messages = find_inconsistent_tags(flac_files, True, True)
    e_messages = {
        flac_files[0]: ["Filename date not four digits."],
        flac_files[1]: ["Artist mismatch: Artist != Artist2"],
    }
    assert e_messages == a_messages
