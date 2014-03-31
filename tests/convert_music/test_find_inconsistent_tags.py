import os
from mutagen.flac import FLAC
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


def test_art_lyrics():
    """Test when everything is valid."""
    pass


def test_alpha_instead_of_numeric():
    """Test when track number and date tags aren't integers."""
    pass


def test_single_digit_track():
    """Test for single digit track numbers. Should be double always."""
    pass


def test_one_valid_two_invalid():
    """Test when one FLAC file is fully valid and another one isn't."""
    pass


def test_two_invalid():
    """Test when two FLAC files have invalid tags."""
    pass
