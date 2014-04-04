from convert_music import find_empty_dirs


def test_no_dirs(tmpdir):
    """Test when mp3 dir has nothing at all in it."""
    mp3_dir = tmpdir.mkdir('mp3')
    expected = []
    actual = find_empty_dirs(str(mp3_dir.realpath()))
    assert expected == actual


def test_files_only(tmpdir):
    """Test when mp3 dir just files in it."""
    mp3_dir = tmpdir.mkdir('mp3')
    expected = []
    mp3_dir.join('file01').ensure(file=True)
    mp3_dir.join('file02').ensure(file=True)
    actual = find_empty_dirs(str(mp3_dir.realpath()))
    assert expected == actual


def test_no_empty_dirs(tmpdir):
    """Test when mp3 dir has non-empty dirs in it."""
    mp3_dir = tmpdir.mkdir('mp3')
    expected = []
    mp3_dir.mkdir('dir01').join('file01').ensure(file=True)
    mp3_dir.mkdir('dir02').join('file02').ensure(file=True)
    actual = find_empty_dirs(str(mp3_dir.realpath()))
    assert expected == actual


def test_dirs_of_empty_dirs(tmpdir):
    """Test to make sure empty subdirectories are detected."""
    mp3_dir = tmpdir.mkdir('mp3')
    # Generate.
    dir01 = str(mp3_dir.join('dir01').ensure(dir=True).realpath())
    dir02 = str(mp3_dir.join('dir02').ensure(dir=True).realpath())
    dir03 = str(mp3_dir.join('dir02').join('dir03').ensure(dir=True).realpath())
    dir04 = str(mp3_dir.join('dir04').ensure(dir=True).realpath())
    expected = [dir04, dir03, dir02, dir01]
    # Test.
    actual = find_empty_dirs(str(mp3_dir.realpath()))
    assert expected == actual


def test_some_empty_dirs(tmpdir):
    """Test when a directory has an empty sub directory, and another subdirectory with a file somewhere in it."""
    mp3_dir = tmpdir.mkdir('mp3')
    # Long empty dir path.
    dir01 = str(mp3_dir.join('dir01').ensure(dir=True).realpath())
    dir02 = str(mp3_dir.join('dir01').join('dir02').ensure(dir=True).realpath())
    dir03 = str(mp3_dir.join('dir01').join('dir02').join('dir03').ensure(dir=True).realpath())
    dir04 = str(mp3_dir.join('dir01').join('dir02').join('dir03').join('dir04').ensure(dir=True).realpath())
    expected = [dir04, dir03, dir02, dir01]
    # Dir with a file somewhere in it.
    dir06 = str(mp3_dir.mkdir('dir05').join('dir06').ensure(dir=True).realpath())
    mp3_dir.join('dir05').mkdir('dir07').join('file01').ensure(file=True)
    expected.insert(0, dir06)
    # Test.
    actual = find_empty_dirs(str(mp3_dir.realpath()))
    assert expected == actual
