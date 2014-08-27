#!/usr/bin/env python2.7
"""Downloads all image metadata from an Imgur account to an XML file.

This application will open a web browser window to Imgur with a PIN code (if
you are logged in). Enter that code in this application right afterwards.

License: MIT
Website: https://github.com/Robpol86/general

Usage: imgur_metadata_backup.py -o FILE

Options:
    -h --help                   Show this screen.
    -o FILE --outfile=FILE      Write XML to this file.
"""

from __future__ import print_function
import json
import os
import signal
import sys
import threading
import webbrowser
from xml.dom import minidom
from xml.etree import ElementTree

from docopt import docopt
import requests

IMGUR_CLIENT_ID = 'bb1944e2c2f2d07'
IMGUR_SECRET_ID = 'c0b901eaeda4d0621d6b43619aa99e9f357b9a08'  # I don't believe in security theater.
IMGUR_URL_AUTH_PIN = 'https://api.imgur.com/oauth2/authorize?client_id={}&response_type=pin'.format(IMGUR_CLIENT_ID)
IMGUR_URL_AUTH_TOKEN = 'https://api.imgur.com/oauth2/token'
IMGUR_URL_COUNT = 'https://api.imgur.com/3/account/me/images/count'
IMGUR_URL_IMAGES = 'https://api.imgur.com/3/account/me/images/{}'
OPTIONS = docopt(__doc__) if __name__ == '__main__' else dict()


class QueryThread(threading.Thread):
    """Goes out to Imgur and gets a "page" of image metadata. Up to 50 images in one request."""

    def __init__(self, headers, page):
        super(QueryThread, self).__init__()
        self.headers = headers
        self.url = IMGUR_URL_IMAGES.format(page)
        self.data = None

    def run(self):
        response = requests.get(self.url, headers=self.headers)
        if not response.ok:
            raise RuntimeError('Imgur API returned error! {}'.format(response.text))
        self.data = json.loads(response.text)


def auth():
    """Open a browser window that prompts the user for a PIN code, then ask for that code.

    Returns:
    Headers dict with the user's access_token. Pass this dict into requests.get(headers=).
    """
    print('Opening URL: {}'.format(IMGUR_URL_AUTH_PIN))
    webbrowser.open(IMGUR_URL_AUTH_PIN)
    while True:
        pin = raw_input('Enter the PIN "number": ').strip()
        payload = dict(client_id=IMGUR_CLIENT_ID, client_secret=IMGUR_SECRET_ID, grant_type='pin', pin=pin)
        response = requests.post(IMGUR_URL_AUTH_TOKEN, data=payload)
        if not response.ok:
            print('Authorization failed: {}'.format(response.reason))
            print(response.text)
            print()
            continue
        print('Authorization successful!')
        data = json.loads(response.text)
        return dict(Authorization='Bearer {}'.format(data['access_token']))


def to_xml(images):
    """Converts a dict of image dicts into XML.

    Positional arguments:
    images -- Dict, keys are Imgur image IDs (e.g. psHY2Mx), values are dicts with image metadata.

    Returns:
    XML string.
    """
    xml_top = ElementTree.Element('imgur_metadata_backup')
    xml_images = ElementTree.SubElement(xml_top, 'images')

    # Populate XML chronologically (images) and alphabetically (attributes).
    for image_id in sorted(images, key=lambda i: images[i]['datetime']):
        xml_image = ElementTree.SubElement(xml_images, 'image', dict(id=image_id))
        for key, value in sorted(images[image_id].items()):
            attr = ElementTree.SubElement(xml_image, key)
            attr.text = unicode(value if value is not None else '')

    # Make pretty and return. From http://pymotw.com/2/xml/etree/ElementTree/create.html
    xml_string = ElementTree.tostring(xml_top)
    xml_pretty = minidom.parseString(xml_string)
    return xml_pretty.toprettyxml(indent='  ')


def main():
    if os.path.exists(OPTIONS['--outfile']):
        print('ERROR: Outfile exists: {}'.format(OPTIONS['--outfile']), file=sys.stderr)
        sys.exit(1)

    # Get headers and number of images.
    headers = auth()
    count = int(json.loads(requests.get(IMGUR_URL_COUNT, headers=headers).text)['data'])

    # Query. Too lazy to implement rate limiting or throttling right now, I only have like 10 pages.
    threads = [QueryThread(headers, page) for page in range(count // 50 + 1)]
    print('Starting {} threads.'.format(len(threads)))
    for thread in threads:
        thread.start()
    print('Waiting for all threads to finish.')
    for thread in threads:
        thread.join()
        print('{} {} finished.'.format(thread.name, thread.url))

    # Merge into one big dictionary of dictionaries.
    images = {i.pop('id'): i for t in threads for i in t.data['data']}
    missing = count - len(images)
    if missing:
        print('WARNING: {} image(s) missing for some reason.'.format(missing))

    # Save XML to file.
    xml_string = to_xml(images)
    with open(OPTIONS['--outfile'], 'wb') as f:
        f.write(xml_string.encode('utf-8'))
    print('Successfully wrote file.')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))  # Properly handle Control+C
    main()
