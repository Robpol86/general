import json
import os
import pytest
from mutagen.id3 import ID3, COMM
from convert_music import find_files


def test_no_mp3s(tmpdir):
    """Test when there's a few FLACs and no mp3s."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    for i in range(1, 5):
        flac = flac_dir.join('Artist - 2014 - Album - {:02d} - Title.flac'.format(i)).ensure(file=True)
        e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    flac = flac_dir.mkdir('Artist2').join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    e_create_dirs.append(str(mp3_dir.join('Artist2').realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files


def test_no_flacs_no_mp3s(tmpdir):
    """Test when there are no valid files in either directory."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    flac_dir.join('Artist2 - 2012 - Album - 01 - Title.wav').ensure(file=True)
    with pytest.raises(IOError):
        find_files(str(flac_dir.realpath()), str(mp3_dir.realpath()))


def test_orphan_mp3(tmpdir):
    """Test when an mp3 exists but no equivalent FLAC exists."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist - 2014 - Album - 01 - Title.mp3').ensure(file=True)
    e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    e_deleted_mp3s.append(str(mp3.realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files


def test_blank_mp3s(tmpdir):
    """Test when there are mp3s with no id3 tags."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    e_deleted_mp3s.append(str(mp3.realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files


def test_yes_id3_no_comments(tmpdir):
    """Test when an mp3 has id3 tags but no comment tag."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    id3 = ID3(str(mp3.realpath()))
    id3.delete()
    id3.save()
    e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    e_deleted_mp3s.append(str(mp3.realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files


def test_invalid_comments(tmpdir):
    """Test when an mp3 has a comment tag but invalid data."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    id3 = ID3(str(mp3.realpath()))
    id3.delete()
    id3.add(COMM(encoding=3, lang="eng", desc="", text="Test"))
    id3.save(v1=2)
    e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    e_deleted_mp3s.append(str(mp3.realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files


def test_old_comments(tmpdir):
    """Test when an mp3 has valid JSON in comment tag, but the files have changed since the data was recorded."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    comment = json.dumps(dict(flac_mtime=0, flac_size=0, mp3_mtime=0, mp3_size=0))
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    id3 = ID3(str(mp3.realpath()))
    id3.delete()
    id3.add(COMM(encoding=3, lang="eng", desc="", text=comment))
    id3.save(v1=2)
    e_flac_files[str(flac.realpath())] = [int(flac.mtime()), 0]
    e_deleted_mp3s.append(str(mp3.realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files


def test_perfect_match(tmpdir):
    """Test to make sure nothing needs to be done when everything is up to date."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    # Prepare.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    id3 = ID3(str(mp3.realpath()))
    id3.delete()
    id3.add(COMM(encoding=3, lang="eng", desc="", text=(' ' * 200)))  # Pad ID3 tag and get final size first.
    id3.save(v1=2)
    mtime = int(mp3.mtime())
    comment = json.dumps(dict(
        flac_mtime=int(flac.mtime()), flac_size=int(flac.size()), mp3_mtime=mtime, mp3_size=int(mp3.size())
    ))
    id3.add(COMM(encoding=3, lang="eng", desc="", text=comment))  # Now put in real data.
    id3.save(v1=2)
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert dict() == a_flac_files
    assert list() == a_delete_mp3s
    assert list() == a_create_dirs
    assert list() == a_foreign_files


def test_foreign_files(tmpdir):
    """Test when a non-mp3 file is in the mp3 directory."""
    flac_dir = tmpdir.mkdir('flac')
    mp3_dir = tmpdir.mkdir('mp3')
    e_flac_files = dict()
    e_deleted_mp3s = list()
    e_create_dirs = list()
    e_foreign_files = list()
    # Prepare.
    flac = flac_dir.join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    mp3 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp3').ensure(file=True)
    foreign_1 = mp3_dir.join('Artist2 - 2012 - Album - 01 - Title.mp4').ensure(file=True)
    foreign_2 = mp3_dir.mkdir('testdir').join('Artist2 - 2012 - Album - 01 - Title.flac').ensure(file=True)
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.mp3'), 'rb') as f:
        mp3.write(f.read(), 'wb')
    id3 = ID3(str(mp3.realpath()))
    id3.delete()
    id3.add(COMM(encoding=3, lang="eng", desc="", text=(' ' * 200)))  # Pad ID3 tag and get final size first.
    id3.save(v1=2)
    mtime = int(mp3.mtime())
    comment = json.dumps(dict(
        flac_mtime=int(flac.mtime()), flac_size=int(flac.size()), mp3_mtime=mtime, mp3_size=int(mp3.size())
    ))
    id3.add(COMM(encoding=3, lang="eng", desc="", text=comment))  # Now put in real data.
    id3.save(v1=2)
    e_foreign_files.append(str(foreign_1.realpath()))
    e_foreign_files.append(str(foreign_2.realpath()))
    # Test.
    a_flac_files, a_delete_mp3s, a_create_dirs, a_foreign_files = find_files(str(flac_dir.realpath()),
                                                                             str(mp3_dir.realpath()))
    assert e_flac_files == a_flac_files
    assert e_deleted_mp3s == a_delete_mp3s
    assert e_create_dirs == a_create_dirs
    assert e_foreign_files == a_foreign_files
