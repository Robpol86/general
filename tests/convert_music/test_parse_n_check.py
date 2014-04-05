import pytest
from docopt import docopt
from convert_music import __doc__ as convert_music__doc__, parse_n_check


def test_good_values(capsys, threads):
    """Test for valid values."""
    config_expected = dict(
        flac_bin='/bin/bash',
        lame_bin='/bin/bash',
        ignore_art=False,
        ignore_lyrics=False,
        threads=threads,
        flac_dir='/tmp',
        mp3_dir='/tmp',
        quiet=False,
    )
    argv = ['/tmp/', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash']
    cli_config_settings = parse_n_check(docopt(convert_music__doc__, argv=argv))
    assert config_expected == cli_config_settings
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = ""
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual


def test_alpha_threads(capsys):
    """Test for non-numeric threads value."""
    argv = ['/tmp', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash', '--threads=abc']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "--threads is not an integer or is zero: abc\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual


def test_zero_threads(capsys):
    """Test for zero threads value."""
    argv = ['/tmp', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash', '--threads=0']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "--threads is not an integer or is zero: 0\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual


def test_paths_not_exist(capsys):
    """Makes sure the proper error occurs when specifying a path that doesn't exist."""
    argv = ['/does_not_exist', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "<flac_dir> is not a directory or does not exist: /does_not_exist\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual

    argv = ['/tmp', '/does_not_exist', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "<mp3_dir> is not a directory or does not exist: /does_not_exist\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual

    argv = ['/tmp', '/tmp', '--flac-bin-path=/does_not_exist', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "--flac-bin-path is not a file or does not exist: /does_not_exist\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual

    argv = ['/tmp', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/does_not_exist']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "--lame-bin-path is not a file or does not exist: /does_not_exist\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual


def test_paths_not_readable(capsys):
    """Makes sure the proper error occurs when specifying a path that exists but has no read permissions."""
    argv = ['/var/db/sudo', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "<flac_dir> is not readable or no execute permissions: /var/db/sudo\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual

    argv = ['/tmp', '/var/db/sudo', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "<mp3_dir> is not readable, writable, or no execute permissions: /var/db/sudo\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual

    argv = ['/tmp', '/tmp', '--flac-bin-path=/etc/sudoers', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "--flac-bin-path is not readable or no execute permissions: /etc/sudoers\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual

    argv = ['/tmp', '/tmp', '--flac-bin-path=/bin/bash', '--lame-bin-path=/etc/sudoers']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "--lame-bin-path is not readable or no execute permissions: /etc/sudoers\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual


def test_paths_not_writable(capsys):
    """Test for mp3_dir that is readable but not writable."""
    argv = ['/tmp', '/etc/pam.d/', '--flac-bin-path=/bin/bash', '--lame-bin-path=/bin/bash']
    with pytest.raises(ValueError):
        parse_n_check(docopt(convert_music__doc__, argv=argv))
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = ""
    stderr_expected = "<mp3_dir> is not readable, writable, or no execute permissions: /etc/pam.d\n"
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual
