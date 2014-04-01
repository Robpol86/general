#!/usr/bin/env python2.7
"""Converts all FLAC files to mp3 files, maintaining id3 tags.
License: MIT; Website: https://github.com/Robpol86/general

Usage:
    convert_music.py <flac_dir> <mp3_dir> [-ay] [-f FILE] [-l FILE] [-t NUM]
    convert_music.py (-h | --help)
    convert_music.py --version

Options:
    -a --ignore-art                 Ignore checks for missing album art.
    -f FILE --flac-bin-path=FILE    Specify path to flac binary file.
                                    [default: /usr/bin/flac]
    -l FILE --lame-bin-path=FILE    Specify path to lame (mp3) binary file.
                                    [default: /usr/bin/lame]
    -t NUM --threads=NUM            Thread count.
                                    [default: automatic]
    -y --ignore-lyrics              Ignore checks for missing lyric data.
"""
import atexit
import fnmatch
import json
import logging
import logging.config
import os
import signal
import sys
from docopt import docopt
from mutagen.flac import FLAC, error
from mutagen.id3 import ID3
from color_logging_misc import LoggingSetup, Color


__program__ = 'convert_music'
__version__ = '0.0.1'


def find_files(flac_dir, mp3_dir):
    """Finds FLAC and mp3 files. Returns list of FLAC files to be converted, and list of mp3 files to be deleted.
    FLAC files that don't need converting (and mp3 files that don't need deleting) are omitted. Metadata is stored in
    mp3 file id3 tags under "comments". This function uses that metadata to determine which files do what.

    Positional arguments:
    flac_dir -- parent directory string which holds source FLAC files.
    mp3_dir -- parent directory string which holds destination mp3 files.

    Returns (tuple):
    flac_files -- dictionary of FLAC file paths (keys) and 2-value lists (values), [file mtime, file byte size].
    delete_mp3s -- list of mp3 files to be deleted.
    create_dirs -- list of directories that need to be created in the destination parent directory for future mp3s.
    """
    flac_files = dict()  # {/file/path.flac: [mtime, bytesize]}
    delete_mp3s = list()  # List of mp3 file paths to be deleted.
    create_dirs = list()  # Directories to be created in mp3_dir.
    # First find every single FLAC file and store it in the flac_files dictionary.
    for root, _, files in os.walk(flac_dir):
        for path in (os.path.join(root, filename) for filename in fnmatch.filter(files, '*.flac')):
            stat = os.stat(path)
            flac_files[path] = [int(stat.st_mtime), int(stat.st_size)]
    if not flac_files:
        # No FLAC files found at all, wrong directory maybe.
        raise IOError
    # Find every single mp3, and decide its fate with its own metadata.
    for path in (os.path.join(r, f) for r, _, fl in os.walk(mp3_dir) for f in fnmatch.filter(fl, '*.mp3')):
        flac_equivalent = path.replace(mp3_dir, flac_dir).replace('.mp3', '.flac')
        if flac_equivalent not in flac_files:
            # The FLAC file this mp3 file was previously converted from has been moved or deleted. Delete this mp3.
            delete_mp3s.append(path)
            continue
        try:
            metadata = json.loads(getattr(ID3(path).get("COMM::'eng'"), 'text', [None])[0])
        except (TypeError, ValueError):
            # The mp3 file is corrupt. Something happened to it after this script created it in the past.
            delete_mp3s.append(path)
            continue
        stat = os.stat(path)
        metadata_expected = dict(
            flac_mtime=flac_files[flac_equivalent][0], flac_size=flac_files[flac_equivalent][1],
            mp3_mtime=int(stat.st_mtime), mp3_size=int(stat.st_size)
        )
        if metadata != metadata_expected:
            # Something has changed with either files.
            delete_mp3s.append(path)
            continue
        # Made it this far. That means nothing has changed with the mp3 or FLAC. Removing FLAC from "convert me" list.
        flac_files.pop(flac_equivalent)
    # Figure out which directories should be created.
    for directory in {os.path.dirname(f.replace(flac_dir, mp3_dir)) for f in flac_files}:
        if not os.path.exists(directory):
            create_dirs.append(directory)
    create_dirs.sort()
    return flac_files, delete_mp3s, create_dirs


def find_inconsistent_tags(flac_filepaths, ignore_art=False, ignore_lyrics=False):
    """Look for missing data in FLAC 'id3' tags or tags that don't match the filename.

    Positional arguments:
    flac_filepaths -- list of FLAC file paths to read metadata from.

    Keyword arguments:
    ignore_art -- ignore checking if FLAC file has album art embedded in it, boolean.
    ignore_lyrics -- ignore checking if FLAC file has lyrics embedded in it, boolean.

    Returns:
    Dictionary with keys being FLAC file paths and values being a list of warnings to be printed about id3 tags.
    """
    tag_names = ['artist', 'date', 'album', 'tracknumber', 'title']
    messages = {p: [] for p in flac_filepaths}
    for path in flac_filepaths:
        # Verify filename.
        split = os.path.splitext(os.path.basename(path))[0].split(' - ')
        if len(split) != 5:
            messages[path].append("Filename doesn't have five items.")
            continue
        f_artist, f_date, f_album, f_track, f_title = split
        # Verify basic tags.
        try:
            tags = FLAC(path)
        except error:
            messages[path].append("Invalid file.")
            continue
        t_artist, t_date, t_album, t_track, t_title = [tags.get(i, [''])[0] for i in tag_names]
        if f_artist != t_artist:
            messages[path].append("Artist mismatch: {} != {}".format(f_artist, t_artist))
        if f_album != t_album:
            messages[path].append("Album mismatch: {} != {}".format(f_album, t_album))
        if f_title != t_title:
            messages[path].append("Title mismatch: {} != {}".format(f_title, t_title))
        # Verify numeric tags.
        if not f_date.isdigit():
            messages[path].append("Filename date not a number.")
        elif len(f_date) != 4:
            messages[path].append("Filename date not four digits.")
        elif f_date != t_date:
            messages[path].append("Date mismatch: {} != {}".format(f_date, t_date))
        if not f_track.isdigit():
            messages[path].append("Filename track number not a number.")
        elif len(f_track) != 2:
            messages[path].append("Filename track number not two digits.")
        elif f_track != t_track:
            messages[path].append("Track number mismatch: {} != {}".format(f_track, t_track))
        # Check for lyrics and album art.
        if not ignore_art and not tags.pictures:
            messages[path].append("No album art.")
        if not ignore_lyrics and not tags.get('unsyncedlyrics', [False])[0]:
            messages[path].append("No lyrics.")
    # Return dict of messages without empty lists.
    return {k: v for k, v in messages.items() if v}


def main(config):
    logger = logging.getLogger('%s.main' % __name__)

    logger.info("Finding files and verifying tags...")
    try:
        flac_files, delete_mp3s, create_dirs = find_files(config['flac_dir'], config['mp3_dir'])
    except IOError:
        logger.error("No FLAC files found in directory {}".format(config['flac_dir']))
        sys.exit(1)
    tag_warnings = find_inconsistent_tags(flac_files.keys(), config['ignore_art'], config['ignore_lyrics'])
    logger.info('; '.join([
        "{} new FLAC {}".format(len(flac_files), 'file' if len(flac_files) == 1 else 'files'),
        "{} new {}".format(len(create_dirs), 'directory' if len(create_dirs) == 1 else 'directories'),
        "{} FLAC {}".format(len(tag_warnings), 'warning' if len(tag_warnings) == 1 else 'warnings'),
        "{} {} to delete".format(len(delete_mp3s), 'mp3' if len(delete_mp3s) == 1 else 'mp3s'),
    ]))

    # Delete mp3s with user's permission.
    if delete_mp3s:
        logger.info(Color("{yellow}The following files need to be deleted:{/yellow}"))
        for path in delete_mp3s:
            logger.info(path)
        raw_input(Color("{b}Press Enter to delete these files.{/b}"))
        for path in delete_mp3s:
            os.remove(path)

    # Notify user of inconsistencies in FLAC id3 tags and file names.
    if tag_warnings:
        logger.info(Color("{yellow}The following inconsistencies have been found in id3 tags/file names:{/yellow}"))
        printed_before = False
        for path, warnings in tag_warnings.items():
            if len(warnings) == 1:
                printed_before = True
                logger.info('{}: {}'.format(os.path.basename(path), warnings[0]))
            else:
                if printed_before:
                    print
                    printed_before = False
                logger.info('{}:'.format(os.path.basename(path)))
                for warning in warnings:
                    logger.info(warning)
                print
        raw_input(Color("{b}Press Enter to continue anyway.{/b}"))

    # Create directories.
    for directory in create_dirs:
        os.makedirs(directory)

    # Start the conversion.
    # TODO


def parse_n_check(docopt_config):
    """Re-formats dict from docopt and does some sanity checks on it.

    Positional arguments:
    docopt_config -- dictionary from docopt.docopt().

    Returns:
    Dictionary similar to docopt_config but only relevant data without CLI notation.
    """
    logger = logging.getLogger('%s.parse_n_check' % __name__)
    config = dict(
        flac_bin=os.path.abspath(os.path.expanduser(docopt_config.get('--flac-bin-path'))),
        lame_bin=os.path.abspath(os.path.expanduser(docopt_config.get('--lame-bin-path'))),
        ignore_art=bool(docopt_config.get('--ignore-art')),
        ignore_lyrics=bool(docopt_config.get('--ignore-lyrics')),
        threads=docopt_config.get('--threads'),
        flac_dir=os.path.abspath(os.path.expanduser(docopt_config.get('<flac_dir>'))),
        mp3_dir=os.path.abspath(os.path.expanduser(docopt_config.get('<mp3_dir>'))),
    )
    # Sanity checks.
    if config['threads'] == 'automatic':
        config['threads'] = os.sysconf('SC_NPROCESSORS_ONLN') or 1
    elif not isinstance(config['threads'], int) or not config['threads']:
        logger.error("--threads is not an integer or is zero: {}".format(config['threads']))
        raise ValueError
    if not os.path.isfile(config['flac_bin']):
        logger.error("--flac-bin-path is not a file or does not exist: {}".format(config['flac_bin']))
        raise ValueError
    if not os.access(config['flac_bin'], os.R_OK|os.X_OK):
        logger.error("--flac-bin-path is not readable or no execute permissions: {}".format(config['flac_bin']))
        raise ValueError
    if not os.path.isfile(config['lame_bin']):
        logger.error("--lame-bin-path is not a file or does not exist: {}".format(config['lame_bin']))
        raise ValueError
    if not os.access(config['lame_bin'], os.R_OK|os.X_OK):
        logger.error("--lame-bin-path is not readable or no execute permissions: {}".format(config['lame_bin']))
        raise ValueError
    if not os.path.isdir(config['flac_dir']):
        logger.error("<flac_dir> is not a directory or does not exist: {}".format(config['flac_dir']))
        raise ValueError
    if not os.access(config['flac_dir'], os.R_OK|os.X_OK):
        logger.error("<flac_dir> is not readable or no execute permissions: {}".format(config['flac_dir']))
        raise ValueError
    if not os.path.isdir(config['mp3_dir']):
        logger.error("<mp3_dir> is not a directory or does not exist: {}".format(config['mp3_dir']))
        raise ValueError
    if not os.access(config['mp3_dir'], os.W_OK|os.R_OK|os.X_OK):
        logger.error("<mp3_dir> is not readable, writable, or no execute permissions: {}".format(config['mp3_dir']))
        raise ValueError
    return config


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda a, b: sys.exit(0))  # Properly handle Control+C
    try:
        cli_config_settings = parse_n_check(docopt(__doc__, version=__version__))
    except ValueError:
        sys.exit(1)

    # Initialize logging.
    with LoggingSetup() as cm:
        logging.config.fileConfig(cm.config)  # Setup logging.
    sys.excepthook = lambda t, v, b: logging.critical("Uncaught exception!", exc_info=(t, v, b))  # Log exceptions.
    atexit.register(lambda: logging.info("%s pid %d shutting down." % (__program__, os.getpid())))  # Log when exiting.
    logging.info("Starting %s version %s" % (__program__, __version__))

    # Run the program.
    main(cli_config_settings)
