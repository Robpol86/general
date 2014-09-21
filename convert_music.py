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
                                    [default: /usr/local/bin/flac]
    -l FILE --lame-bin-path=FILE    Specify path to lame (mp3) binary file.
                                    [default: /usr/local/bin/lame]
    -t NUM --threads=NUM            Thread count.
                                    [default: automatic]
    -y --ignore-lyrics              Ignore checks for missing lyric data.
"""

from __future__ import division, print_function
import Queue
import fnmatch
import json
import logging
import logging.config
import os
import signal
import subprocess
import sys
import threading
import time

from colorclass import Color
from docopt import docopt
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, error as flac_error
from mutagen.id3 import ID3, APIC, USLT, COMM, error as id3_error

__version__ = '0.1.0'
OPTIONS = docopt(__doc__) if __name__ == '__main__' else dict()
PAD_COMMENT = 200  # Pad ID3 comment tag by this many spaces.


class Song(object):
    """An instance of a single song."""

    INSTANCES = set()  # Overwritten once.

    def __init__(self, flac_path, flac_dir, mp3_dir):
        # Derive data from file path.
        self.flac_path = flac_path
        self.flac_name = os.path.basename(flac_path)
        self.mp3_path = flac_path.replace(flac_dir, mp3_dir)[:-5] + '.mp3'
        self.mp3_name = os.path.basename(self.mp3_path)
        split = os.path.basename(self.flac_name)[:-5].split(' - ')
        self.filename_artist, self.filename_date, self.filename_album, self.filename_track, self.filename_title = split

        self.flac_current_mtime = None
        self.flac_current_size = None
        self.mp3_current_mtime = None
        self.mp3_current_size = None

        self.flac_stored_mtime = None
        self.flac_stored_size = None
        self.mp3_stored_mtime = None
        self.mp3_stored_size = None

        self.flac_artist = ''
        self.flac_date = ''
        self.flac_album = ''
        self.flac_disc = ''
        self.flac_track = ''
        self.flac_title = ''
        self.flac_has_lyrics = False
        self.flac_has_picture = False

    def get_metadata(self):
        flac_stat = os.stat(self.flac_path)
        self.flac_current_mtime, self.flac_current_size = int(flac_stat.st_mtime), int(flac_stat.st_size)
        if os.path.exists(self.mp3_path):
            mp3_stat = os.stat(self.mp3_path)
            self.mp3_current_mtime, self.mp3_current_size = int(mp3_stat.st_mtime), int(mp3_stat.st_size)

        try:
            flac_tags = FLAC(self.flac_path)
        except flac_error:
            pass
        else:
            self.flac_artist = flac_tags.get('artist', [''])[0]
            self.flac_date = flac_tags.get('date', [''])[0]
            self.flac_album = flac_tags.get('album', [''])[0]
            self.flac_disc = flac_tags.get('discnumber', [''])[0]
            self.flac_track = flac_tags.get('tracknumber', [''])[0]
            self.flac_title = flac_tags.get('title', [''])[0]
            self.flac_has_lyrics = bool(flac_tags.get('unsyncedlyrics', [False])[0])
            self.flac_has_picture = bool(flac_tags.pictures)

        if not os.path.exists(self.mp3_path):
            return

        try:
            mp3_tags = ID3(self.mp3_path)
        except id3_error:
            pass
        else:
            stored_metadata = json.loads(getattr(mp3_tags.get("COMM::'eng'"), 'text', ['{}'])[0])
            self.flac_stored_mtime = stored_metadata.get('flac_mtime')
            self.flac_stored_size = stored_metadata.get('flac_size')
            self.mp3_stored_mtime = stored_metadata.get('mp3_mtime')
            self.mp3_stored_size = stored_metadata.get('mp3_size')

    @property
    def bad_artist(self):
        return self.filename_artist != self.flac_artist

    @property
    def bad_date(self):
        if len(self.filename_date) != 4:
            return True
        if not self.filename_date.isdigit():
            return True
        return self.filename_date != self.flac_date

    @property
    def bad_album(self):
        if self.filename_album == self.flac_album:
            return False
        if self.filename_album == '{} (Disc {})'.format(self.flac_album, self.flac_disc):
            return False
        return True

    @property
    def bad_track(self):
        if len(self.filename_track) not in (2, 3):
            return True
        if not self.filename_track.isdigit():
            return True
        return self.filename_track != self.flac_track

    @property
    def bad_title(self):
        return self.filename_title != self.flac_title

    @property
    def bad_lyrics(self):
        if OPTIONS.get('--ignore-lyrics', False):
            return False
        return not self.flac_has_lyrics

    @property
    def bad_picture(self):
        if OPTIONS.get('--ignore-art', False):
            return False
        return not self.flac_has_picture

    @property
    def metadata_ok(self):
        status = [self.bad_artist, self.bad_date, self.bad_album, self.bad_track, self.bad_title, self.bad_lyrics,
                  self.bad_picture]
        return not any(status)

    @property
    def skip_conversion(self):
        status = [
            self.flac_current_mtime == self.flac_stored_mtime,
            self.flac_current_size == self.flac_stored_size,
            self.mp3_current_mtime == self.mp3_stored_mtime,
            self.mp3_current_size == self.mp3_stored_size,
        ]
        return all(status)


def error(message, code=1):
    """Prints an error message to stderr and exits with a status of 1 by default."""
    if message:
        print('ERROR: {}'.format(message), file=sys.stderr)
    else:
        print(file=sys.stderr)
    sys.exit(code)






class ConvertFiles(threading.Thread):
    """Threaded class that does the actual file conversion. This also copies over the id3 tags.

    Class variables are to be set before threads are started.

    Class variables:
    flac_bin -- file path to the FLAC binary. It handles decompressing FLAC files to wav files.
    lame_bin -- file path to the lame binary. It handles compressing wav files into mp3 files.
    """
    flac_bin = ''
    lame_bin = ''

    def __init__(self, queue):
        """
        Positional arguments:
        queue -- Queue.Queue() instance, items are 4-value tuples: ('flac_path', 'temp_wav', 'temp_mp3', 'final_mp3').
        """
        super(ConvertFiles, self).__init__()
        self.queue = queue

    def run(self):
        """The main body of the thread. Loops until queue is empty."""
        logger = logging.getLogger('ConvertFiles.run.{}'.format(self.name))
        logging.debug('Worker thread started.')
        while True:
            try:
                source_flac_path, temp_wav_path, temp_mp3_path, destination_mp3_path = self.queue.get_nowait()
            except Queue.Empty:
                break
            logging.debug('Source FLAC path: {}'.format(source_flac_path))
            logging.debug('Temporary wav path: {}'.format(temp_wav_path))
            logging.debug('Temporary mp3 path: {}'.format(temp_mp3_path))
            logging.debug('Final mp3 path: {}'.format(destination_mp3_path))
            self.convert(source_flac_path, temp_wav_path, temp_mp3_path)
            self.write_tags(source_flac_path, temp_mp3_path)
            os.rename(temp_mp3_path, destination_mp3_path)
            logging.debug('Done converting this file.')
        logging.debug('Worker thread exiting.')

    def convert(self, source_flac_path, temp_wav_path, temp_mp3_path):
        """Converts the FLAC file into an mp3 file with a temporary filename."""
        logger = logging.getLogger('ConvertFiles.convert.{}'.format(self.name))
        # First decompress.
        command = [self.flac_bin, '--silent', '--decode', '-o', temp_wav_path, source_flac_path]
        logging.debug('Command: {}'.format(' '.join(command)))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() is None:
            time.sleep(0.2)  # Wait for process to finish.
        code = process.returncode
        stdout, stderr = process.communicate()
        logging.debug('code: {}; stdout: {}; stderr: {};'.format(code, stdout, stderr))
        if code:
            raise RuntimeError('Process {} returned {}; stdout: {}; stderr: {};'.format(self.flac_bin, code, stdout,
                                                                                        stderr))
        # Then compress.
        command = [self.lame_bin, '--quiet', '-h', '-V0', temp_wav_path, temp_mp3_path]
        logging.debug('Command: {}'.format(' '.join(command)))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() is None:
            time.sleep(0.2)  # Wait for process to finish.
        code = process.returncode
        stdout, stderr = process.communicate()
        logging.debug('code: {}; stdout: {}; stderr: {};'.format(code, stdout, stderr))
        if code:
            raise RuntimeError('Process {} returned {}; stdout: {}; stderr: {};'.format(self.lame_bin, code, stdout,
                                                                                        stderr))
        # Delete wav file by-product.
        logging.debug('Removing: {}'.format(temp_wav_path))
        os.remove(temp_wav_path)

    @staticmethod
    def write_tags(source_flac_path, temp_mp3_path):
        """Write mp3 id3 tags from tags available in the FLAC file. Also save metadata as JSON to mp3 comment tag."""
        # Copy non-picture/non-lyric tags from FLAC to mp3.
        tags, id3 = FLAC(source_flac_path), EasyID3(temp_mp3_path)
        for tag in (t for t in tags if t in EasyID3.valid_keys.keys()):
            id3[tag] = tags[tag]
        id3.save(v1=2)
        # Copy pictures/lyrics from FLAC to mp3.
        id3 = ID3(temp_mp3_path)
        id3.add(COMM(encoding=3, lang='eng', desc='', text=(' ' * 200)))  # Pad ID3 tag to keep final size the same.
        if tags.pictures:
            pic = tags.pictures[0]
            id3.add(APIC(encoding=0, mime=pic.mime, type=int(pic.type), desc=pic.desc, data=pic.data))
        if 'unsyncedlyrics' in tags:
            id3.add(USLT(encoding=0, lang='eng', desc='Lyrics', text=unicode(tags['unsyncedlyrics'][0])))
        id3.save(v1=2)
        # Save metadata to id3 comments tag.
        flac_stat, mp3_stat = os.stat(source_flac_path), os.stat(temp_mp3_path)
        comment = json.dumps(dict(
            flac_mtime=int(flac_stat.st_mtime), flac_size=int(flac_stat.st_size),
            mp3_mtime=int(mp3_stat.st_mtime), mp3_size=int(mp3_stat.st_size)
        ))
        id3.add(COMM(encoding=3, lang='eng', desc='', text=comment))
        id3.save(v1=2)


def find_files(flac_dir, mp3_dir):
    """Finds FLAC and mp3 files. Returns a tuple of different data (refer to Returns section in this docstring).
    FLAC files that don't need converting (and mp3 files that don't need deleting) are omitted. Metadata is stored in
    mp3 file id3 tags under "comments". This function uses that metadata to determine which files do what.

    Positional arguments:
    flac_dir -- parent directory string which holds source FLAC files.
    mp3_dir -- parent directory string which holds destination mp3 files.

    Returns (tuple):
    flac_files -- dictionary of FLAC file paths (keys) and 2-value lists (values), [file mtime, file byte size].
    delete_mp3s -- list of mp3 files to be deleted.
    create_dirs -- list of directories that need to be created in the destination parent directory for future mp3s.
    foreign_files -- list of non-mp3 files in the mp3 directory which interfere with find_empty_dirs().
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

    # Find non-mp3 files in the mp3 directory.
    foreign_files = sorted([os.path.join(r, f) for r, _, fl in os.walk(mp3_dir) for f in fl if not f.endswith('.mp3')])

    # Figure out which directories should be created.
    for directory in {os.path.dirname(f.replace(flac_dir, mp3_dir)) for f in flac_files}:
        if not os.path.exists(directory):
            create_dirs.append(directory)
    create_dirs.sort()
    return flac_files, delete_mp3s, create_dirs, foreign_files


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
        except flac_error:
            messages[path].append('Invalid file.')
            continue
        t_artist, t_date, t_album, t_track, t_title = [tags.get(i, [''])[0] for i in tag_names]
        if f_artist != t_artist:
            messages[path].append('Artist mismatch: {} != {}'.format(f_artist, t_artist))
        if f_album != t_album:
            messages[path].append('Album mismatch: {} != {}'.format(f_album, t_album))
        if f_title != t_title:
            messages[path].append('Title mismatch: {} != {}'.format(f_title, t_title))
        # Verify numeric tags.
        if not f_date.isdigit():
            messages[path].append('Filename date not a number.')
        elif len(f_date) != 4:
            messages[path].append('Filename date not four digits.')
        elif f_date != t_date:
            messages[path].append('Date mismatch: {} != {}'.format(f_date, t_date))
        if not f_track.isdigit():
            messages[path].append('Filename track number not a number.')
        elif len(f_track) != 2:
            messages[path].append('Filename track number not two digits.')
        elif f_track != t_track:
            messages[path].append('Track number mismatch: {} != {}'.format(f_track, t_track))
        # Check for lyrics and album art.
        if not ignore_art and not tags.pictures:
            messages[path].append('No album art.')
        if not ignore_lyrics and not tags.get('unsyncedlyrics', [False])[0]:
            messages[path].append('No lyrics.')
    # Return dict of messages without empty lists.
    return {k: v for k, v in messages.items() if v}


def find_empty_dirs(parent_dir):
    """Returns a list of directories that are empty or contain empty directories.

    Positional arguments:
    parent_dir -- parent directory string to search.

    Returns:
    List of empty directories or directories that contain empty directories. Remove in order for successful execution.
    """
    dirs_to_remove = {r: bool(f) for r, d, f in os.walk(parent_dir)}  # First get all dirs available.
    dirs_to_remove.pop(parent_dir, None)  # If parent_dir is empty don't include it, just focus on subdirectories.
    for directory in sorted(dirs_to_remove.keys(), reverse=True):
        does_dir_have_files = dirs_to_remove.get(directory, False)  # Skip if dir has already been removed from dict.
        if not does_dir_have_files:
            continue
        # Directory has files. Remove entire directory tree from dirs_to_remove.
        dirs_to_remove.pop(directory)
        while directory != parent_dir:
            directory = os.path.split(directory)[0]
            dirs_to_remove.pop(directory, None)
    return sorted(dirs_to_remove, reverse=True)


def main():

    logging.info('Finding files and verifying tags...')
    try:
        flac_files, delete_mp3s, create_dirs, foreign_files = find_files(OPTIONS['flac_dir'], OPTIONS['mp3_dir'])
    except IOError:
        logging.error('No FLAC files found in directory {}'.format(OPTIONS['flac_dir']))
        sys.exit(1)
    tag_warnings = find_inconsistent_tags(flac_files.keys(), OPTIONS['ignore_art'], OPTIONS['ignore_lyrics'])
    logging.info('; '.join([
        '{} new FLAC {}'.format(len(flac_files), 'file' if len(flac_files) == 1 else 'files'),
        '{} new {}'.format(len(create_dirs), 'directory' if len(create_dirs) == 1 else 'directories'),
        '{} FLAC {}'.format(len(tag_warnings), 'warning' if len(tag_warnings) == 1 else 'warnings'),
        '{} {} to delete'.format(len(delete_mp3s), 'mp3' if len(delete_mp3s) == 1 else 'mp3s'),
    ]))

    # Delete mp3s with user's permission.
    if delete_mp3s:
        logging.info(Color('{yellow}The following files need to be deleted:{/yellow}'))
        for path in delete_mp3s:
            logging.info(path)
        raw_input(Color('{b}Press Enter to delete these files.{/b}'))
        for path in delete_mp3s:
            os.remove(path)

    # Notify user of foreign files in mp3 directory.
    if foreign_files:
        logging.info('{yellow}The following non-mp3 files were found:{/yellow}')
        for path in foreign_files:
            logging.info(path)
        raw_input(Color('{b}Press Enter to continue anyway.{/b}'))

    # Notify user of inconsistencies in FLAC id3 tags and file names.
    if tag_warnings:
        logging.info(Color('{yellow}The following inconsistencies have been found in id3 tags/file names:{/yellow}'))
        printed_before = False
        for path, warnings in tag_warnings.items():
            if len(warnings) == 1:
                printed_before = True
                logging.info('{}: {}'.format(os.path.basename(path), warnings[0]))
            else:
                if printed_before:
                    print()
                    printed_before = False
                logging.info('{}:'.format(os.path.basename(path)))
                for warning in warnings:
                    logging.info(warning)
                print()
        raw_input(Color('{b}Press Enter to continue anyway.{/b}'))

    # Create directories.
    for directory in create_dirs:
        os.makedirs(directory)

    # Prepare for conversion.
    ConvertFiles.flac_bin = OPTIONS['flac_bin']
    ConvertFiles.lame_bin = OPTIONS['lame_bin']
    queue = Queue.Queue()
    for flac_file in flac_files:
        mp3_file = flac_file.replace(OPTIONS['flac_dir'], OPTIONS['mp3_dir'])  # Change directories from flac to mp3 dir.
        temp_wav_file = os.path.splitext(mp3_file)[0] + '.wav.part'  # Temporary file while converting (FLAC -> wav).
        temp_mp3_file = os.path.splitext(mp3_file)[0] + '.mp3.part'  # Temporary file while converting (wav -> mp3).
        final_mp3_file = os.path.splitext(mp3_file)[0] + '.mp3'  # Final mp3 filename.
        queue.put((flac_file, temp_wav_file, temp_mp3_file, final_mp3_file))

    # Start the conversion.
    total = len(flac_files)
    count = total
    logging.info('Converting {} file{}:'.format(total, '' if total == 1 else 's'))
    threads = []
    for i in range(OPTIONS['threads']):
        thread = ConvertFiles(queue)
        thread.daemon = True  # Fixes script hang on ctrl+c.
        thread.start()
        threads.append(thread)

    # Wait for everything to finish.
    while count:
        if not OPTIONS['quiet']:
            sys.stdout.write('{}/{} ({:02d}%) files remaining...\r'.format(count, total, count / total))
            sys.stdout.flush()
        time.sleep(1)
        count = queue.qsize() + len([True for t in threads if t.is_alive()])
        # Look for threads that crashed.
        if len([t for t in threads if t.is_alive()]) < OPTIONS['threads']:
            # One or more thread isn't running.
            if queue.qsize():
                # But the queue isn't empty, something bad happened.
                raise RuntimeError('Worker thread(s) prematurely terminated.')

    # Done, now clean up empty directories.
    empty_dirs = find_empty_dirs(OPTIONS['mp3_dir'])
    if empty_dirs:
        logging.info(Color('{yellow}The following empty directories were found:{/yellow}'))
        for path in empty_dirs:
            logging.info(path)
        raw_input(Color('{b}Press Enter to delete these directories.{/b}'))
        for path in delete_mp3s:
            os.rmdir(path)


def validate_options():
    """Re-formats dict from docopt and does some sanity checks on it.

    Positional arguments:
    OPTIONS -- dictionary from docopt.docopt().

    Returns:
    Dictionary similar to OPTIONS but only relevant data without CLI notation.
    """
    logger = logging.getLogger('%s.parse_n_check' % __name__)
    config = dict(
        flac_bin=os.path.abspath(os.path.expanduser(OPTIONS.get('--flac-bin-path'))),
        lame_bin=os.path.abspath(os.path.expanduser(OPTIONS.get('--lame-bin-path'))),
        ignore_art=bool(OPTIONS.get('--ignore-art')),
        ignore_lyrics=bool(OPTIONS.get('--ignore-lyrics')),
        threads=OPTIONS.get('--threads'),
        flac_dir=os.path.abspath(os.path.expanduser(OPTIONS.get('<flac_dir>'))),
        mp3_dir=os.path.abspath(os.path.expanduser(OPTIONS.get('<mp3_dir>'))),
        quiet=False,
    )
    # Sanity checks.
    if OPTIONS['threads'] == 'automatic':
        OPTIONS['threads'] = os.sysconf('SC_NPROCESSORS_ONLN') or 1
    elif not isinstance(OPTIONS['threads'], int) or not OPTIONS['threads']:
        logging.error('--threads is not an integer or is zero: {}'.format(OPTIONS['threads']))
        raise ValueError
    if not os.path.isfile(OPTIONS['flac_bin']):
        logging.error('--flac-bin-path is not a file or does not exist: {}'.format(OPTIONS['flac_bin']))
        raise ValueError
    if not os.access(OPTIONS['flac_bin'], os.R_OK | os.X_OK):
        logging.error('--flac-bin-path is not readable or no execute permissions: {}'.format(OPTIONS['flac_bin']))
        raise ValueError
    if not os.path.isfile(OPTIONS['lame_bin']):
        logging.error('--lame-bin-path is not a file or does not exist: {}'.format(OPTIONS['lame_bin']))
        raise ValueError
    if not os.access(OPTIONS['lame_bin'], os.R_OK | os.X_OK):
        logging.error('--lame-bin-path is not readable or no execute permissions: {}'.format(OPTIONS['lame_bin']))
        raise ValueError
    if not os.path.isdir(OPTIONS['flac_dir']):
        logging.error('<flac_dir> is not a directory or does not exist: {}'.format(OPTIONS['flac_dir']))
        raise ValueError
    if not os.access(OPTIONS['flac_dir'], os.R_OK | os.X_OK):
        logging.error('<flac_dir> is not readable or no execute permissions: {}'.format(OPTIONS['flac_dir']))
        raise ValueError
    if not os.path.isdir(OPTIONS['mp3_dir']):
        logging.error('<mp3_dir> is not a directory or does not exist: {}'.format(OPTIONS['mp3_dir']))
        raise ValueError
    if not os.access(OPTIONS['mp3_dir'], os.W_OK | os.R_OK | os.X_OK):
        logging.error('<mp3_dir> is not readable, writable, or no execute permissions: {}'.format(OPTIONS['mp3_dir']))
        raise ValueError
    return config


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: error('', 0))  # Properly handle Control+C
    main()
