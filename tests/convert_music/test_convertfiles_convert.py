import os
import textwrap
import pytest
from convert_music import ConvertFiles


def test_success(tmpdir, capsys):
    """Test convert_music.ConvertFiles.convert with good data."""
    # Prepare.
    flac = tmpdir.mkdir('flac').join('song.flac').ensure(file=True)
    mp3_dir = tmpdir.mkdir('mp3')
    with open(os.path.join(os.path.dirname(__file__), '1khz_sine.flac'), 'rb') as f:
        flac.write(f.read(), 'wb')
    source_flac_path = str(flac.realpath())
    temp_wav_path = str(mp3_dir.join('song.wav.part'))
    temp_mp3_path = str(mp3_dir.join('song.mp3.part'))
    ConvertFiles.flac_bin = '/usr/bin/flac'
    ConvertFiles.lame_bin = '/usr/bin/lame'
    # Test.
    ConvertFiles(None).convert(source_flac_path, temp_wav_path, temp_mp3_path)
    # Check.
    assert not os.path.exists(temp_wav_path)  # Should have been deleted at the end of .convert().
    assert os.path.isfile(temp_mp3_path)
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = textwrap.dedent("""\
        Command: {flac_bin} --silent --decode -o {temp_wav_path} {source_flac_path}
        code: 0; stdout: ; stderr: ;
        Command: {mp3_bin} --quiet -h -V0 {temp_wav_path} {temp_mp3_path}
        code: 0; stdout: ; stderr: ;
        Removing: {temp_wav_path}
    """).format(flac_bin='/usr/bin/flac', mp3_bin='/usr/bin/lame', temp_wav_path=temp_wav_path,
                temp_mp3_path=temp_mp3_path, source_flac_path=source_flac_path)
    stderr_expected = ''
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual


def test_bad_flac(tmpdir, capsys):
    """Test with corrupt FLAC file."""
    # Prepare.
    flac = tmpdir.mkdir('flac').join('song.flac').ensure(file=True)
    mp3_dir = tmpdir.mkdir('mp3')
    source_flac_path = str(flac.realpath())
    temp_wav_path = str(mp3_dir.join('song.wav.part'))
    temp_mp3_path = str(mp3_dir.join('song.mp3.part'))
    ConvertFiles.flac_bin = '/usr/bin/flac'
    ConvertFiles.lame_bin = '/usr/bin/lame'
    # Test.
    with pytest.raises(RuntimeError) as e:
        ConvertFiles(None).convert(source_flac_path, temp_wav_path, temp_mp3_path)
    # Check.
    error = '\nsong.flac: ERROR while decoding metadata\n           state = FLAC__STREAM_DECODER_END_OF_STREAM\n'
    assert e.value.message == 'Process {} returned {}; stdout: {}; stderr: {};'.format('/usr/bin/flac', 1, '', error)
    assert not os.path.exists(temp_wav_path)  # Should have been deleted at the end of .convert().
    assert not os.path.isfile(temp_mp3_path)
    stdout_actual, stderr_actual = capsys.readouterr()
    stdout_expected = textwrap.dedent("""\
        Command: {flac_bin} --silent --decode -o {temp_wav_path} {source_flac_path}
        code: 1; stdout: ; stderr: {error};
    """).format(flac_bin='/usr/bin/flac', temp_wav_path=temp_wav_path, source_flac_path=source_flac_path, error=error)
    stderr_expected = ''
    assert stdout_expected == stdout_actual
    assert stderr_expected == stderr_actual
