#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
# terrible OPDS server
# Copyright (C) 2023  Chris Clark
"""Uses WSGI, see http://docs.python.org/library/wsgiref.html
Python 2 or Python 3
"""

import logging
import os
import mimetypes
import socket
import struct
import sys
import time

try:
    # py2 (and <py3.8)
    from cgi import parse_qs
except ImportError:
    # py3
    from urllib.parse import parse_qs

# TODO use a real XML library

from wsgiref.simple_server import make_server

try:
    import bjoern
except ImportError:
    bjoern = None


log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(level=logging.DEBUG)


def determine_local_ipaddr():
    local_address = None

    # Most portable (for modern versions of Python)
    if hasattr(socket, 'gethostbyname_ex'):
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith('127.'):
                local_address = ip
                break
    # may be none still (nokia) http://www.skweezer.com/s.aspx/-/pypi~python~org/pypi/netifaces/0~4 http://www.skweezer.com/s.aspx?q=http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib has alonger one

    if sys.platform.startswith('linux'):
        import fcntl

        def get_ip_address(ifname):
            ifname = ifname.encode('latin1')
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15])
            )[20:24])

        if not local_address:
            for devname in os.listdir('/sys/class/net/'):
                try:
                    ip = get_ip_address(devname)
                    if not ip.startswith('127.'):
                        local_address = ip
                        break
                except IOError:
                    pass

    # Jython / Java approach
    if not local_address and InetAddress:
        addr = InetAddress.getLocalHost()
        hostname = addr.getHostName()
        for ip_addr in InetAddress.getAllByName(hostname):
            if not ip_addr.isLoopbackAddress():
                local_address = ip_addr.getHostAddress()
                break

    if not local_address:
        # really? Oh well lets connect to a remote socket (Google DNS server)
        # and see what IP we use them
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 53))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith('127.'):
            local_address = ip

    return local_address


# FIXME use ISO Z instead
# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def header_format_date_time(timestamp):
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )

def current_timestamp_for_header():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    #return header_format_date_time(time.time())


def to_bytes(in_str):
    # could choose to only encode for Python 3+
    return in_str.encode('utf-8')


def not_found(environ, start_response):
    """serves 404s."""
    #start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
    #return ['Not Found']
    start_response('404 NOT FOUND', [('Content-Type', 'text/html')])
    return [to_bytes('''<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL /??????? was not found on this server.</p>
</body></html>''')]


config = {}
config['ebook_dir'] = os.environ.get('EBOOK_DIR', os.path.abspath('testbooks'))
WEBOOK_SELF_URL_PATH = os.environ['WEBOOK_SELF_URL_PATH']

##### TODO move into webok_core

# FIXME from webook_server.py
ebook_only_mimetypes = {
    'cbr': 'application/x-cbr',  # TODO cbt and cb7
    'cbz': 'application/x-cbz',  # application/vnd.comicbook+zip
    'epub': 'application/epub+zip',
    'epub3': 'application/epub+zip',
    'fb2': 'text/fb2+xml',  # application/fb2
    'mobi': 'application/x-mobipocket-ebook',
    'txt': 'text/plain',

    # UNTESTED
    'djv': 'image/vnd.djvu',
    'djvu': 'image/vnd.djvu',  # application/djvu image/x-djvu

    'htm': 'text/html',
    'html': 'text/html',
    'pdf': 'application/pdf',
    'xhtml': 'application/xhtml+xml',

    # Images
    'gif': 'image/gif',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',

    # TODO more formats
}

def guess_mimetype(filename):
    """Guess mimetype based on filename (rather than content). Returns string.
    """
    # FIXME not sure this is very efficient
    ebook_format = os.path.splitext(filename)[-1].lower()  # TODO if .zip back trace in case we have .fb2.zip, .rtf.zip, .txt.zip, etc.
    ebook_format = ebook_format[1:]  # removing leading '.'
    mimetype_str = ebook_only_mimetypes.get(ebook_format, 'application/octet-stream')  # TODO consider fallback to mimetypes.guess_type(os_path)[0]
    return mimetype_str

class BootMeta:
    def __init__(self, filename):
        self.filename = os.path.abspath(filename)  # expected to be absolute (relative would work)

    @property
    def author(self):
        """Guess author name based on filename (rather than content). Returns string:
            Lastname, Firstname
        Currently assumes single author
        """
        # TODO add guess logic based on filename OR dig into metadata if exists
        return ''  # or None?

    @property
    def mimetype(self):
        """Guess mimetype based on filename (rather than content). Returns string.
        """
        # FIXME not sure this is very efficient
        filename = os.path.basename(self.filename)
        return guess_mimetype(filename)

    @property
    def title(self):
        """Guess book title based on filename (rather than content). Returns string.
        """
        filename = os.path.basename(self.filename)  # bother messing with file extension?
        return filename


##### TODO move into webok_core

def opds_search(environ, start_response):
    # Returns a dictionary in which the values are lists
    if environ.get('QUERY_STRING'):
        get_dict = parse_qs(environ['QUERY_STRING'])
    else:
        get_dict = {}
    q = get_dict.get('q')  # same as most search engines
    #print('get_dict=%r'% get_dict)
    if not q:
        return not_found(environ, start_response)
    log.info('search term q=%r', q)

    result = [to_bytes(
'''<?xml version="1.0" encoding="UTF-8"?>
  <feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/" xmlns:opds="http://opds-spec.org/2010/catalog">
      <title>Catalog in /</title>
      <id>/</id>
      <link rel="start" href="/" type="application/atom+xml;profile=opds-catalog;kind=navigation"></link>
      <updated>2023-01-01T10:53:39-08:00</updated><!-- TODO FIXME implement timestamp for now -->

      <!-- koreader does NOT need an icon -->

      <link rel="search" type="application/opensearchdescription+xml" title="Project Gutenberg Catalog Search" href="{WEBOOK_SELF_URL_PATH}/search-metadata.xml"/>  <!-- TODO FIXME hard coded URL :-(  -->
    <opensearch:itemsPerPage>25</opensearch:itemsPerPage>
    <opensearch:startIndex>1</opensearch:startIndex>

'''.format(WEBOOK_SELF_URL_PATH=WEBOOK_SELF_URL_PATH))]

    search_term = q[0]  # TODO think this is correct, rather than concat all
    search_term = search_term.lower()  # for now single search term, case insensitive compare
    directory_path = config['ebook_dir']
    directory_path_len = len(directory_path) + 1  # +1 is the directory seperator (assuming Unix or Windows paths)
    join = os.path.join  # for performance, rather than reduced typing
    log.info('searching file system')
    for root, dirs, files in os.walk(directory_path):
        for dir_name in dirs:
            # any directory names that hit
            tmp_path = join(root, dir_name)
            tmp_path_sans_prefix = tmp_path[directory_path_len:]
            if search_term in tmp_path_sans_prefix.lower():
                # FIXME escaping missing - template and/or xml API usage
                result.append(to_bytes('''
      <entry>
          <title>{tmp_path_sans_prefix}/</title>
          <id>{tmp_path_sans_prefix}</id>
          <link rel="subsection" href="/browse/{tmp_path_sans_prefix}" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="{tmp_path_sans_prefix}"></link>
      </entry>
'''.format(tmp_path_sans_prefix=tmp_path_sans_prefix)))

        for file_name in files:
            # any file names that hit
            tmp_path = join(root, file_name)
            tmp_path_sans_prefix = tmp_path[directory_path_len:]
            if search_term in tmp_path_sans_prefix.lower():
                # TODO include file size?
                # TODO try and guess title and author name
                # TODO is there a way to get "book information" link to work?
                result.append(to_bytes('''
    <entry>
        <title>{tmp_path_sans_prefix}</title>
        <author>
            <name>{author_name_surname_first}</name>
        </author>
        <id>{tmp_path_sans_prefix}</id>
        <link type="application/octet-stream" rel="http://opds-spec.org/acquisition" title="Raw" href="/file/{tmp_path_sans_prefix}"/><!-- koreader will hide and not display this due to unsupported mime-type -->
        <link type="{mime_type}" rel="http://opds-spec.org/acquisition" title="Original" href="/file/{tmp_path_sans_prefix}"/>
        <link type="application/epub+zip" rel="http://opds-spec.org/acquisition" title="EPUB convert" href="/epub/{tmp_path_sans_prefix}"/>
        <link type="application/x-mobipocket-ebook" rel="http://opds-spec.org/acquisition" title="Kindle (mobi) convert" href="/mobi/{tmp_path_sans_prefix}"/>
    </entry>
'''.format(
        tmp_path_sans_prefix=tmp_path_sans_prefix,
        author_name_surname_first='lastname, firstname',
        mime_type="application/epub+zip"  #'application/octet-stream'  # FIXME choosing something koreader does not support results in option being invisible
        # unclear on text koreader charset encoding. content-type for utf-8 = "text/plain; charset=utf-8"
        )))
    log.info('search of file system complete')

    #log.error('NotImplemented search support')
    #return not_found(environ, start_response)

    status = '200 OK'
    headers = [
                ('Content-type', 'application/xml'),  # "application/atom+xml; charset=UTF-8"
                ('Cache-Control', 'no-cache, must-revalidate'),
                ('Pragma', 'no-cache'),
                ]

    result.append(to_bytes('''  </feed>
'''))
    start_response(status, headers)
    return result

def opds_search_meta(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'application/xml')]
    result = []

    result.append(to_bytes(
'''<?xml version="1.0" encoding="UTF-8"?>

<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
   <LongName>webook_server - Worst E-book server</LongName>
   <ShortName>webook_server</ShortName>
   <Description>Search the webook_server ebook catalog.</Description>
   <Tags>ebooks books</Tags>
   <Developer>Chris Clark</Developer>
   <!-- 
   <Contact>email@goes.here.org</Contact>
   -->


   <Url type="application/atom+xml"
        template="{WEBOOK_SELF_URL_PATH}/opds/search?q={{searchTerms}}"/>
   <!-- 
   TODO FIXME hard coded URL
   -->

   <Query role="example" searchTerms="shakespeare hamlet" />
   <Query role="example" searchTerms="doyle detective" />
   <Query role="example" searchTerms="love stories" />

   <SyndicationRight>open</SyndicationRight>
   <Language>en-us</Language>
   <OutputEncoding>UTF-8</OutputEncoding>
   <InputEncoding>UTF-8</InputEncoding>
</OpenSearchDescription>

'''.format(WEBOOK_SELF_URL_PATH=WEBOOK_SELF_URL_PATH)  # NOTE searchTerms is escaped so as to preserve {searchTerms}
    ))

    headers.append(('Content-Length', str(len(result[0]))))  # in case WSGI server does not implement this
    headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache

    start_response(status, headers)
    return result


def opds_browse(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'application/atom+xml;profile=opds-catalog;kind=acquisition')]
    result = []

    directory_path_split = environ['PATH_INFO'].split('/', 2)  # /file/some/path
    log.info('directory_path_split  %s', directory_path_split)

    try:
        directory_path = directory_path_split[2]
    except IndexError:
        # got /file rather than /file/
        directory_path = ''
    log.info('browse %r', directory_path)

    if directory_path:
        directory_path = os.path.normpath(directory_path)
        os_path = os.path.join(config['ebook_dir'], directory_path)
        if os.path.isdir(os_path):
            directory_path = directory_path + '/'
    else:
        os_path = config['ebook_dir']
        directory_path = ''
    log.info('directory_path %s', directory_path)
    log.info('os_path %s', os_path)

    if os.path.isfile(os_path):
        log.error('serve file')
        try:
            f = open(os_path, 'rb')
        except IOError:
            return not_found(environ, start_response)  # FIXME return a better error for internal server error
        content_type = guess_mimetype(os_path)
        headers = [('Content-type', content_type)]
        # TODO headers, date could be from filesystem
        start_response(status, headers)
        return f

    files = os.listdir(os_path)
    for filename in files:
        file_path = os.path.join(os_path, filename)
        """
        size = str(os.path.getsize(file_path))
        date = os.path.getmtime(file_path)
        date = time.gmtime(date)
        date = time.strftime('%d-%b-%Y %H:%M', date)  # match Apache/Nginix date format (todo option for ISO)
        spaces1 = ' '*(50-len(filename))
        spaces2 = ' '*(20-len(size))
        """
        # FIXME cgi escape needed!
        if os.path.isdir(file_path):
                result.append(to_bytes('''
      <entry>
          <title>{filename}/</title>
          <id>{filename}</id>
          <link rel="subsection" href="{href_path}" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="{filename}"></link>
      </entry>
'''.format(filename=filename, href_path='/file/' + directory_path  + filename)))  # href need full path (/file/.....) not relative...
                # FIXME TODO /file should be take from directory_path_split in case of /epub, etc.
                #print(result[-1])
        else:
            # got a file (maybe an slink)
            metadata = BootMeta(file_path)
            # TODO include file size?
            # TODO try and guess title and author name
            # TODO is there a way to get "book information" link to work?
            result.append(to_bytes('''
    <entry>
        <title>{title}</title>
        <author>
            <name>{author_name_surname_first}</name>
        </author>
        <id>{filename}</id>
        <link type="application/octet-stream" rel="http://opds-spec.org/acquisition" title="Raw" href="{href_path}"/><!-- koreader will hide and not display this due to unsupported mime-type -->
        <link type="{mime_type}" rel="http://opds-spec.org/acquisition" title="Original" href="{href_path}"/>
        <link type="application/epub+zip" rel="http://opds-spec.org/acquisition" title="EPUB convert" href="{href_path_epub}"/>
        <link type="application/x-mobipocket-ebook" rel="http://opds-spec.org/acquisition" title="Kindle (mobi) convert" href="{href_path_mobi}"/>
    </entry>
'''.format(
        author_name_surname_first=metadata.author,  #'lastname, firstname',
        filename=filename,  # FIXME need full path for href?
        href_path='/file/' + directory_path  + filename,
        href_path_epub='/epub/' + directory_path  + filename,
        href_path_mobi='/mobi/' + directory_path  + filename,
        mime_type=metadata.mimetype,  #"application/epub+zip",  #'application/octet-stream'  # FIXME choosing something koreader does not support results in option being invisible
        # unclear on text koreader charset encoding. content-type for utf-8 = "text/plain; charset=utf-8"
        title=metadata.title
        )))

    headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache - koreader will show old directory info
    start_response(status, headers)
    return result


def opds_root(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'application/atom+xml;profile=opds-catalog;kind=acquisition')]
    result = []

    if environ['SERVER_PROTOCOL'] == 'HTTP/1.0':
        log.error('SERVER_PROTOCOL is too old, koreader needs ast least "HTTP/1.1"')
        raise NotImplementedError('SERVER_PROTOCOL is too old')

    path_info = environ['PATH_INFO']
    print(repr(path_info))

    if path_info == '/search-metadata.xml':
        return opds_search_meta(environ, start_response)
    if path_info.startswith('/opds/search'):
        return opds_search(environ, start_response)
    if path_info.startswith('/file'):
        return opds_browse(environ, start_response)
    if path_info != '/':
        return not_found(environ, start_response)

    result.append(to_bytes(
'''<?xml version="1.0" encoding="UTF-8"?>
  <feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/" xmlns:opds="http://opds-spec.org/2010/catalog">
      <title>Catalog in /</title>
      <id>/</id>
      <link rel="start" href="/" type="application/atom+xml;profile=opds-catalog;kind=navigation"></link>
      <updated>2023-01-01T10:53:39-08:00</updated><!-- TODO FIXME implement timestamp for now -->

      <!-- koreader does NOT need an icon -->

      <link rel="search" type="application/opensearchdescription+xml" title="Project Gutenberg Catalog Search" href="{WEBOOK_SELF_URL_PATH}/search-metadata.xml"/>  <!-- TODO FIXME hard coded URL :-(  -->
    <opensearch:itemsPerPage>25</opensearch:itemsPerPage>
    <opensearch:startIndex>1</opensearch:startIndex>

      <entry>
          <title>BROWSE</title>
          <id>BROWSE</id>
          <link rel="subsection" href="/file/" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="BROWSE"></link>
      </entry>

      <entry>
          <title>demo_file.txt</title>
          <id>/demo_file.txt</id>
          <link rel="http://opds-spec.org/acquisition" href="/demo_file.txt" type="text/plain; charset=utf-8" title="aaa_text.txt"></link>
<link type="application/epub+zip" rel="http://opds-spec.org/acquisition" title="EPUB (no images)" length="260729" href="https://www.gutenberg.org/ebooks/174.epub.noimages"/>
<link type="application/x-mobipocket-ebook" rel="http://opds-spec.org/acquisition" title="Kindle (no images)" length="398836" href="https://www.gutenberg.org/ebooks/174.kindle.noimages"/>
          <published></published>
          <updated></updated>
      </entry>

      <entry>
          <title>comics_dir/</title>
          <id>/comics_dir</id>
          <link rel="subsection" href="/comics_dir" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="comics"></link>
          <published></published>
          <updated></updated>
      </entry>

    <entry>
        <title>The Picture of Dorian Gray</title>
        <author>
            <name>Surname, Firstname</name>
        </author>
        <id>some_sort_of_unique_id</id>
        <link type="application/epub+zip" rel="http://opds-spec.org/acquisition" title="Original" href="/file/path/here_orig"/>
        <link type="application/epub+zip" rel="http://opds-spec.org/acquisition" title="EPUB" href="/file/path/here1"/>
        <link type="application/x-mobipocket-ebook" rel="http://opds-spec.org/acquisition" title="Kindle (mobi)" href="/file/path/here2"/>
    </entry>

  </feed>
'''.format(WEBOOK_SELF_URL_PATH=WEBOOK_SELF_URL_PATH)
            ))

    headers.append(('Content-Length', str(len(result[0]))))  # in case WSGI server does not implement this
    headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache

    start_response(status, headers)
    return result


def main(argv=None):
    argv = argv or sys.argv
    print('Python %s on %s' % (sys.version, sys.platform))
    listen_port = int(os.environ.get('LISTEN_PORT', 8080))
    listen_address = os.environ.get('LISTEN_ADDRESS', '0.0.0.0')  # default to listen publically
    local_ip = determine_local_ipaddr()
    log.info('Listen on: %r', (listen_address, listen_port))
    log.info('Starting server: http://%s:%d', local_ip, listen_port)
    if bjoern:
        log.info('Using: bjoern')
        bjoern.run(opds_root, listen_address, listen_port)
    else:
        log.info('Using: wsgiref.simple_server')
        httpd = make_server(listen_address, listen_port, opds_root)
        httpd.serve_forever()


if __name__ == "__main__":
    sys.exit(main())


