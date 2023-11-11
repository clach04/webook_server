#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
# terrible OPDS server that also supports regular (html) web browsers
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
    from cgi import escape
    from cgi import parse_qs
    from urllib import quote
    #from urllib import quote_plus as quote
except ImportError:
    # py3 - 3.8+
    from html import escape
    from urllib.parse import parse_qs
    from urllib.parse import quote
    #from urllib.parse import quote_plus as quote

# TODO use a real XML library

import wsgiref.simple_server

try:
    import bjoern
except ImportError:
    bjoern = None

try:
    import cheroot
    import cheroot.wsgi
except ImportError:
    cheroot = None

try:
    import cherrypy
except ImportError:
    cherrypy = None

try:
    import werkzeug
    import werkzeug.serving
except ImportError:
    werkzeug = None

import ebook_conversion
from webook_core import BootMeta, ebook_only_mimetypes, guess_mimetype, find_recent_files, load_config, ORDER_DESCENDING

is_py3 = sys.version_info >= (3,)

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(level=logging.DEBUG)


def safe_mkdir(newdir):
    """Create directory path(s) ignoring "already exists" errors, essentially `mkdir -p`"""
    result_dir = os.path.abspath(newdir)
    try:
        os.makedirs(result_dir)
    except OSError as info:
        if info.errno == 17 and os.path.isdir(result_dir):
            pass
        else:
            raise


def determine_local_ipaddr():
    local_address = None

    # Most portable for py2 and 3
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    if not ip.startswith('127.'):
        local_address = ip

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
        # and see what public IP we use them
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


def xml_escape(in_str):
	#return in_str
	return in_str.replace('<', '&#60;').replace('>', '&#62;')  # works with koreader
	#return in_str.replace('<', '&lt;').replace('>', '&gt;')  # untested

def to_bytes(in_str):
    # could choose to only encode for Python 3+
    return in_str.encode('utf-8')

def filename_sanitize(filename):
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition
    # https://datatracker.ietf.org/doc/html/rfc5987
    # apparently latin1 (iso-8859-1) is fine, be more strict and restrict to 7-bit ascii
    # limited attempt to restrict to alpha-numeric
    filename = filename.replace(':', '')
    filename = filename.replace(';', '')
    filename = filename.replace('&', '')
    filename = filename.replace('"', '')
    filename = filename.replace("'", '')
    filename = filename.encode('us-ascii', errors='ignore')  # remove non-ascii
    filename = filename.decode('us-ascii')
    return filename

def filename_rfc6266(filename):
    return quote(filename)

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


CLIENT_OPDS = 'OPDS'
CLIENT_BROWSER = 'browser'

def determine_client(environ):
    """heuristic for determining if we have an OPDS client or a web browser
    """
    log.info('determine client type')
    """client sniffing/determination

    cURL client
        HTTP_ACCEPT = '*/*'
        HTTP_USER_AGENT = 'curl/8.0.1'

    OPDS client
        HTTP_USER_AGENT = 'KOReader/2022.08 (https://koreader.rocks/) LuaSocket/3.0-rc1'

    Web Browser
        HTTP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0'
        HTTP_ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    """
    client_http_accept = environ.get('HTTP_ACCEPT', '')
    log.debug('HTTP_ACCEPT %r', client_http_accept)
    #client_http_user_agent = environ.get('HTTP_USER_AGENT', '')  # not needed/used (yet)
    #log.debug('HTTP_USER_AGENT %r', client_http_user_agent)
    if 'html' in client_http_accept:
        client_type = CLIENT_BROWSER
    else:
        client_type = CLIENT_OPDS
    return client_type

# NOTE global config - see webook_core.load_config()
global config
config = {}

def get_template(template_filename):
    f = open(os.path.join(os.path.dirname(__file__), 'templates', template_filename), 'rb')
    template_string = f.read()
    f.close()
    template_string = template_string.decode('utf-8')
    return template_string

def browser_recent(environ, start_response):
    """Browser client only, find recently updated files
    no parameters, possible TODO items; limit number of files and order
    """
    log.info('browser_recent')
    status = '200 OK'

    client_type = determine_client(environ)
    if client_type == CLIENT_BROWSER:
        headers = [
                    ('Content-Type', 'text/html'),  # "application/atom+xml; charset=UTF-8"
                    ('Cache-Control', 'no-cache, must-revalidate'),
                    ('Pragma', 'no-cache'),
                    ('Last-Modified', current_timestamp_for_header()),
                ]
    start_response(status, headers)

    number_of_files = 50
    sort_order = ORDER_DESCENDING
    search_term = 'RECENT %d' % number_of_files

    log.debug('yield head')
    if client_type == CLIENT_BROWSER:
        yield to_bytes('''<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>webook results {search_term}</title>
    </head>
    <body>
        <h1>webook results {search_term}</h1>

        <pre>
<a href="../">../</a>
'''.format(search_term=escape(search_term))
    )
        search_hit_template = '''<a href="/file/{url}">{url}</a><br>'''

    log.debug('pre recent search')
    # find all recent files before returning any results
    directory_path = config['ebook_dir']
    directory_path_len = len(directory_path) + 1  # +1 is the directory seperator (assuming Unix or Windows paths)
    recent_file_list = find_recent_files(directory_path, number_of_files=number_of_files, order=sort_order)

    log.debug('pre recent for loop')
    for file_name in recent_file_list:
        tmp_path_sans_prefix = file_name[directory_path_len:]
        #results.append(tmp_path_sans_prefix)
        # TODO include file size?
        url = tmp_path_sans_prefix
        if client_type == CLIENT_BROWSER:
            yield to_bytes(search_hit_template.format(url=escape(url)))

    if client_type == CLIENT_BROWSER:
        yield to_bytes('''
        </pre>
    </body>
</html>
''')

def browser_search(environ, start_response):
    """Handles/serves

        /search

    Similar to opds_search()
    TODO GET and POST support
    """
    log.info('browser_search')
    template_filename = 'browser_search.html'
    template_string = get_template(template_filename)

    # Returns a dictionary in which the values are lists
    if environ.get('QUERY_STRING'):
        get_dict = parse_qs(environ['QUERY_STRING'])
    else:
        get_dict = {}
    search_term = get_dict.get('q')  # same as most search engines
    log.info('search search_term %s', search_term)
    if search_term:
        search_term = search_term[0]  # the first one
    #print('get_dict=%r'% get_dict)
    log.info('search search_term %s', search_term)

    status = '200 OK'
    headers = [('Content-Type', 'text/html')]
    result = []


    if not search_term:
        result.append(to_bytes(template_string))  # TODO replace with template (with replacement markers/variables)
        headers.append(('Content-Length', str(len(result[0]))))  # in case WSGI server does not implement this
        headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache

        start_response(status, headers)
        #return result
        yield result[0]
        return
        #return render_template('search.html')  # TODO
    #raise NotImplementedError()

    # actually do search
    headers = [
                ('Content-Type', 'text/html'),  # "application/atom+xml; charset=UTF-8"
                ('Cache-Control', 'no-cache, must-revalidate'),
                ('Pragma', 'no-cache'),
                ('Last-Modified', current_timestamp_for_header()),
            ]
    start_response(status, headers)

    # TODO regex?
    search_term = search_term.lower()  # for now single search term, case insensitive compare
    directory_path = config['ebook_dir']
    directory_path_len = len(directory_path) + 1  # +1 is the directory seperator (assuming Unix or Windows paths)
    join = os.path.join  # for performance, rather than reduced typing

    log.debug('yield head')
    yield to_bytes('''<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>webook results {search_term}</title>
    </head>
    <body>
        <h1>webook results {search_term}</h1>

        <pre>
<a href="../">../</a>
'''.format(search_term=escape(search_term))
    )

    search_hit_template = '''<a href="/file/{url}">{url}</a><br>'''

    log.debug('pre for')
    #results = []  # TODO yield results?
    for root, dirs, files in os.walk(directory_path):
        for dir_name in dirs:
            tmp_path = join(root, dir_name)
            tmp_path_sans_prefix = tmp_path[directory_path_len:]
            if search_term in tmp_path_sans_prefix.lower():
                #results.append(tmp_path_sans_prefix + '/')  # when appended add trailing slash for directories, avoid Flask oddness
                url = tmp_path_sans_prefix + '/'  # make clear a dir with trailing slash
                yield to_bytes(search_hit_template.format(url=escape(url)))
        for file_name in files:
            tmp_path = join(root, file_name)
            tmp_path_sans_prefix = tmp_path[directory_path_len:]
            if search_term in tmp_path_sans_prefix.lower():
                #results.append(tmp_path_sans_prefix)
                # TODO include file size?
                url = tmp_path_sans_prefix
                yield to_bytes(search_hit_template.format(url=escape(url)))

    yield to_bytes('''
        </pre>
    </body>
</html>
''')

    #return render_template('search_results.html', search_term=search_term, urls=results, ebook_format='file')  # TODO


def opds_search(environ, start_response):
    """Handles/serves

        /opds/search

    For OPDS clients. Similar to browser_search()
    """
    log.info('opds_search')
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
      <updated></updated><!-- TODO FIXME implement UTC ISO timestamp string for now -->

      <!-- koreader does NOT need an icon -->

      <link rel="search" type="application/opensearchdescription+xml" title="webook Catalog Search" href="{WEBOOK_SELF_URL_PATH}/search-metadata.xml"/>
    <opensearch:itemsPerPage>25</opensearch:itemsPerPage>
    <opensearch:startIndex>1</opensearch:startIndex>

'''.format(WEBOOK_SELF_URL_PATH=config['self_url_path']))]

    search_term = q[0]  # TODO think this is correct, rather than concat all
    search_term = search_term.lower()  # for now single search term, case insensitive compare
    directory_path = config['ebook_dir']
    directory_path_len = len(directory_path) + 1  # +1 is the directory seperator (assuming Unix or Windows paths)
    join = os.path.join  # for performance, rather than reduced typing
    file_counter = 0
    log.info('searching file system')
    #log.debug('directory_path %r', directory_path)
    #log.debug('directory_path_len %r', directory_path_len)
    #log.debug('test path  %r', os.path.join(directory_path, '1234567.890')[directory_path_len:])
    for root, dirs, files in os.walk(directory_path):
        for dir_name in dirs:
            # any directory names that hit
            tmp_path = join(root, dir_name)
            tmp_path_sans_prefix = tmp_path[directory_path_len:]
            if search_term in tmp_path_sans_prefix.lower():
                file_counter += 1
                # FIXME escaping missing - template and/or xml API usage
                result.append(to_bytes('''
      <entry>
          <title>{title}/</title>
          <id>{tmp_path_sans_prefix}</id>
          <link rel="subsection" href="/file/{tmp_path_sans_prefix}" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="{tmp_path_sans_prefix}"></link>
      </entry>
'''.format(
        title=escape(dir_name, quote=True),
        tmp_path_sans_prefix=quote(tmp_path_sans_prefix))))

        for file_name in files:
            # any file names that hit
            tmp_path = join(root, file_name)
            tmp_path_sans_prefix = tmp_path[directory_path_len:]
            if search_term in tmp_path_sans_prefix.lower():
                metadata = BootMeta(tmp_path_sans_prefix)
                # TODO include file size?
                # TODO try and guess title and author name
                # TODO is there a way to get "book information" link to work?
                result.append(to_bytes('''
    <entry>
        <title>{title}</title>
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
        title=xml_escape(metadata.title),  # quote(metadata.title),   # ends up with escaping showing  in koreader # koreader fails to parse when filename contains single quotes if using: escape(file_name, quote=True), - HOWEVER koreader will fail if <> are left unescaped.
        tmp_path_sans_prefix=quote(tmp_path_sans_prefix),
        author_name_surname_first=metadata.author,
        mime_type=metadata.mimetype  #'application/octet-stream'  # FIXME choosing something koreader does not support results in option being invisible
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
                ('Last-Modified', current_timestamp_for_header()),
                ]

    if file_counter == 0:
        result.append(to_bytes('''
    <entry>
        <title>No records found.</title>
    </entry>
'''))

    result.append(to_bytes('''  </feed>
'''))
    start_response(status, headers)
    return result

def opds_search_meta(environ, start_response):
    """Handles/serves

        /search-metadata.xml
    """
    log.info('opds_search_meta')
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

   <Query role="example" searchTerms="shakespeare hamlet" />
   <Query role="example" searchTerms="doyle detective" />
   <Query role="example" searchTerms="love stories" />

   <SyndicationRight>open</SyndicationRight>
   <Language>en-us</Language>
   <OutputEncoding>UTF-8</OutputEncoding>
   <InputEncoding>UTF-8</InputEncoding>
</OpenSearchDescription>

'''.format(WEBOOK_SELF_URL_PATH=config['self_url_path'])  # NOTE searchTerms is escaped so as to preserve {searchTerms}
    ))

    headers.append(('Content-Length', str(len(result[0]))))  # in case WSGI server does not implement this
    headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache

    start_response(status, headers)
    return result


def opds_browse(environ, start_response):
    """Browse directory and handles/serves

        /file
        /epub
        /fb2
        /fb2.zip
        /mobi
        /txt

    To either OPDS client or web (html) client.
    """
    log.info('opds_browse')
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

    try:
        operation_requested = directory_path_split[1]
    except IndexError:
        # missing, so assume browsing for file
        operation_requested = 'file'
    log.info('operation_requested %r', operation_requested)

    if directory_path:
        directory_path = os.path.normpath(directory_path)
        os_path = os.path.join(config['ebook_dir'], directory_path)
        if os.path.isdir(os_path):
            directory_path = directory_path + '/'
    else:
        os_path = config['ebook_dir']
        directory_path = ''
    log.info('directory_path %s', directory_path)  # requested URL path
    log.info('os_path %s', os_path)  # actual path on disk

    if os.path.isfile(os_path):
        log.info('serve file')
        existing_ebook_format = os.path.splitext(os_path)[-1].lower()
        existing_ebook_format = existing_ebook_format[1:]  # removing leading '.'
        log.info('serve existing_ebook_format %r', existing_ebook_format)
        do_conversion = True
        if existing_ebook_format == operation_requested or operation_requested in ('file'):
            do_conversion = False
            operation_requested = existing_ebook_format
            book_to_serve = os_path
        result_ebook_filename =  os.path.basename(os_path)

        if do_conversion:
            # do conversion
            # TODO consider file caching (see note below about deleting/cleanup of temp files)
            log.info('convert ebook from %s into %s', os_path, operation_requested)
            # TODO if same format, do not convert
            # TODO use meta data in file to generate filename
            #result_ebook_filename = 'fixme_generate_filename.' + operation_requested
            result_ebook_filename = os.path.splitext(result_ebook_filename)[0] + '.' + operation_requested  # NOTE unsure if koreader will pay attention to this filename
            tmp_ebook_filename = 'fixme_generate_filename.' + operation_requested
            tmp_ebook_filename = os.path.join(config['temp_dir'], tmp_ebook_filename)

            # could delete if already exists
            if os.path.exists(tmp_ebook_filename):
                os.remove(tmp_ebook_filename)

            # simple caching support
            if not os.path.exists(tmp_ebook_filename):
                ebook_conversion.convert(os_path, tmp_ebook_filename)
            book_to_serve = tmp_ebook_filename
            # now serve content of tmp_ebook_filename, then potentially delete tmp_ebook_filename

        #check actual extension with operation_requested
        try:
            f = open(book_to_serve, 'rb')
        except IOError:
            return not_found(environ, start_response)  # FIXME return a better error for internal server error
        content_type = guess_mimetype(result_ebook_filename)
        content_disposition = 'attachment; filename="%s"; filename*=utf-8\'\'%s' % (filename_sanitize(result_ebook_filename), filename_rfc6266(result_ebook_filename))  # FIXME TODO rfc-6266
        if not is_py3:
            # if py2 - avoid wsgiref AssertionError: Header values must be strings
            content_disposition = content_disposition.encode('utf-8')  # TODO use to_bytes() instead without if check?
        headers = [
                                ('Content-type', content_type),
                                ('Content-Disposition', content_disposition),
                            ]
        headers.append(('Last-Modified', current_timestamp_for_header()))  # TODO headers, date could be from filesystem
        #log.debug('headers %r', headers)
        start_response(status, headers)
        return f

    log.info('browsing directory')
    client_type = determine_client(environ)

    if client_type == CLIENT_BROWSER:
        # FIXME TODO if missing trailing '/' end up with parent directory...
        log.debug('browse os_path %r', os_path)
        log.info('browse %s', directory_path)
        # format vaugely like Apache and Nginx file browse / auto-index mode
        # TODO use a template
        HTML_HEADER = """<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"><title>Index of {path_title}</title></head><body bgcolor="white"><h1>Index of {path_title}</h1><hr><pre><a href="../">../</a>\n"""
        HTML_FOOTER = "</pre><hr></body></html>"
        path_title = environ['PATH_INFO']
        html = HTML_HEADER.format(path_title=path_title)
        files = os.listdir(os_path)
        for filename in files:  # TODO duplicated code, see OPDS loop below
            file_path = os_path+'/'+filename
            size = str(os.path.getsize(file_path))
            date = os.path.getmtime(file_path)
            date = time.gmtime(date)
            date = time.strftime('%d-%b-%Y %H:%M',date)  # match Apache/Nginix date format (todo option for ISO)
            spaces1 = ' '*(50-len(filename))
            spaces2 = ' '*(20-len(size))
            # FIXME cgi escape needed!
            if os.path.isdir(file_path): html += '<a href="' + escape(filename) + '/">' + escape(filename) + '/</a>'+spaces1+date+spaces2+'   -\n'
            else: html += '<a href="' + escape(filename) + '">' + escape(filename) + '</a>'+spaces1+' '+date+spaces2+size+'\n'
        html += HTML_FOOTER
        headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(html)))]
        headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache - koreader will show old directory info
        start_response(status, headers)
        return [to_bytes(html)]

    # else client_type == CLIENT_OPDS
    result.append(to_bytes('''<?xml version="1.0" encoding="UTF-8"?>
  <feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/" xmlns:opds="http://opds-spec.org/2010/catalog">
      <title>Catalog in /</title>
      <id>/</id>
      <link rel="start" href="/" type="application/atom+xml;profile=opds-catalog;kind=navigation"></link>
      <updated></updated><!-- TODO FIXME implement UTC ISO timestamp string for now -->

      <!-- koreader does NOT need an icon -->

      <link rel="search" type="application/opensearchdescription+xml" title="webook Catalog Search" href="{WEBOOK_SELF_URL_PATH}/search-metadata.xml"/>
    <opensearch:itemsPerPage>25</opensearch:itemsPerPage>
    <opensearch:startIndex>1</opensearch:startIndex>

      <entry>
          <title>BROWSE Root</title>
          <id>BROWSE</id>
          <link rel="subsection" href="/file/" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="BROWSE"></link>
      </entry>

'''.format(WEBOOK_SELF_URL_PATH=config['self_url_path'])
            ))

    files = os.listdir(os_path)
    for filename in files:  # TODO duplicated code, see browser loop code above
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
'''.format(filename=xml_escape(filename), href_path=quote('/file/' + directory_path  + filename))))  # href need full path (/file/.....) not relative...
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
        <id>{title}</id>
        <link type="application/octet-stream" rel="http://opds-spec.org/acquisition" title="Raw" href="/file/{href_path}"/><!-- koreader will hide and not display this due to unsupported mime-type -->
        <link type="{mime_type}" rel="http://opds-spec.org/acquisition" title="Original" href="/file/{href_path}"/>
        <link type="application/epub+zip" rel="http://opds-spec.org/acquisition" title="EPUB convert" href="{href_path_epub}"/>
        <link type="application/x-mobipocket-ebook" rel="http://opds-spec.org/acquisition" title="Kindle (mobi) convert" href="{href_path_mobi}"/>
        <link type="text/plain" rel="http://opds-spec.org/acquisition" title="Text (txt) convert" href="/txt/{href_path}"/>
    </entry>
'''.format(
        author_name_surname_first=metadata.author,  #'lastname, firstname',
        href_path=quote( directory_path  + filename),
        href_path_epub=quote('/epub/' + directory_path  + filename),  # TODO this can be removed, see other hrefs
        href_path_mobi=quote('/mobi/' + directory_path  + filename),  # TODO this can be removed, see other hrefs
        mime_type=metadata.mimetype,  #"application/epub+zip",  #'application/octet-stream'  # FIXME choosing something koreader does not support results in option being invisible
        # unclear on text koreader charset encoding. content-type for utf-8 = "text/plain; charset=utf-8"
        title=xml_escape(metadata.title)
        )))

    result.append(to_bytes('''  </feed>
'''))

    headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache - koreader will show old directory info
    start_response(status, headers)
    return result


def opds_root(environ, start_response):
    """Handles/serves

        /
        i.e. the root, and also handles routing
    """
    log.info('opds_root')
    if not config.get('self_url_path'):
        raise KeyError('self_url_path (or OS variable WEBOOK_SELF_URL_PATH) missing')

    status = '200 OK'
    headers = [('Content-type', 'application/atom+xml;profile=opds-catalog;kind=acquisition')]
    result = []
    client_type = CLIENT_OPDS

    if environ['SERVER_PROTOCOL'] == 'HTTP/1.0':
        log.error('SERVER_PROTOCOL is too old, koreader needs at least "HTTP/1.1"')
        raise NotImplementedError('SERVER_PROTOCOL is too old')

    path_info = environ['PATH_INFO']
    print(repr(path_info))

    if path_info == '/search-metadata.xml':
        return opds_search_meta(environ, start_response)
    if path_info.startswith('/opds/search'):
        return opds_search(environ, start_response)
    if path_info.startswith('/search'):
        return browser_search(environ, start_response)
    if path_info.startswith('/recent'):
        return browser_recent(environ, start_response)

    # below handle any client type
    if path_info.startswith('/file'):
        return opds_browse(environ, start_response)
    if path_info.startswith('/epub'):
        return opds_browse(environ, start_response)
    if path_info.startswith('/fb2'):
        return opds_browse(environ, start_response)
    if path_info.startswith('/fb2.zip'):
        return opds_browse(environ, start_response)
    if path_info.startswith('/mobi'):
        return opds_browse(environ, start_response)
    if path_info.startswith('/txt'):
        return opds_browse(environ, start_response)
    if path_info != '/':
        log.info('Returning ERROR 404 %r', path_info)
        return not_found(environ, start_response)

    client_type = determine_client(environ)

    if client_type == CLIENT_OPDS:
        result.append(to_bytes(
'''<?xml version="1.0" encoding="UTF-8"?>
  <feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/" xmlns:opds="http://opds-spec.org/2010/catalog">
      <title>Catalog in /</title>
      <id>/</id>
      <link rel="start" href="/" type="application/atom+xml;profile=opds-catalog;kind=navigation"></link>
      <updated></updated><!-- TODO FIXME implement UTC ISO timestamp string for now -->

      <!-- koreader does NOT need an icon -->

      <link rel="search" type="application/opensearchdescription+xml" title="webook Catalog Search" href="{WEBOOK_SELF_URL_PATH}/search-metadata.xml"/>
    <opensearch:itemsPerPage>25</opensearch:itemsPerPage>
    <opensearch:startIndex>1</opensearch:startIndex>

      <entry>
          <title>BROWSE</title>
          <id>BROWSE</id>
          <link rel="subsection" href="/file/" type="application/atom+xml;profile=opds-catalog;kind=acquisition" title="BROWSE"></link>
      </entry>

      <!-- TODO add search recent support -->

  </feed>
'''.format(WEBOOK_SELF_URL_PATH=config['self_url_path'])
            ))
    elif client_type == CLIENT_BROWSER:
        headers = [('Content-Type', 'text/html')]
        result.append(to_bytes('''<a href="mobi/">mobi/</a><br>
<a href="epub/">epub/</a><br>
<a href="file/">file/</a><br>
<br>
<a href="search">search</a>
<a href="recent">recent</a>
'''))# TODO loop through ebook_only_mimetypes and list links

    headers.append(('Content-Length', str(len(result[0]))))  # in case WSGI server does not implement this
    headers.append(('Last-Modified', current_timestamp_for_header()))  # many clients will cache

    start_response(status, headers)
    return result


def main(argv=None):
    argv = argv or sys.argv
    print('Python %s on %s' % (sys.version, sys.platform))

    try:
        config_filename = argv[1]
    except IndexError:
        config_filename = 'config.json'
    log.info('Using config file %r', config_filename)

    global config
    config = load_config(config_filename)
    if not config.get('self_url_path'):
        raise KeyError('self_url_path (or OS variable WEBOOK_SELF_URL_PATH) missing')

    log.info('Python %s on %s', sys.version, sys.platform)
    log.info('ebook_conversion %s', ebook_conversion.convert_version())


    listen_port = config['config']['port']
    listen_address = config['config']['host']
    local_ip = determine_local_ipaddr()
    log.info('Listen on: %r', (listen_address, listen_port))
    log.info('OPDS metadata publish URL: %r', (config['self_url_path']))
    log.info('Starting server: http://%s:%d', local_ip, listen_port)
    log.info('using temporary directory temp_dir: %s', config['temp_dir'])
    log.info('Serving from ebook_dir: %s', config['ebook_dir'])

    safe_mkdir(config['temp_dir'])  # if not done, silent errors can occur from tools like Calibre

    if werkzeug:
        log.info('Using: werkzeug %s', werkzeug.__version__)
        #werkzeug.serving.run_simple(listen_address, listen_port, opds_root, use_debugger=True, use_reloader=True)
        werkzeug.serving.run_simple(listen_address, listen_port, opds_root, use_debugger=False, use_reloader=False)
    elif bjoern:
        log.info('Using: bjoern %r', bjoern._bjoern.version)
        bjoern.run(opds_root, listen_address, listen_port)
    elif cheroot:
        log.info('Using: cheroot %s', cheroot.__version__)
        server = cheroot.wsgi.Server((listen_address, listen_port), opds_root)
        server.start()
    elif cherrypy:
        log.info('Using: cherrypy %s', cherrypy.__version__)
        # tested with cherrypy-18.8.0 and cheroot-9.0.0
        # Mount the application
        cherrypy.tree.graft(opds_root, "/")

        # Unsubscribe the default server
        cherrypy.server.unsubscribe()

        # Instantiate a new server object
        server = cherrypy._cpserver.Server()

        # Configure the server object
        server.socket_host = listen_address
        server.socket_port = listen_port
        #server.thread_pool = 30

        # For SSL Support
        # server.ssl_module            = 'pyopenssl'
        # server.ssl_certificate       = 'ssl/certificate.crt'
        # server.ssl_private_key       = 'ssl/private.key'
        # server.ssl_certificate_chain = 'ssl/bundle.crt'

        # Subscribe this server
        server.subscribe()

        # Start the server engine (Option 1 *and* 2)
        cherrypy.engine.start()
        cherrypy.engine.block()
    else:
        log.info('Using: wsgiref.simple_server %s', wsgiref.simple_server.__version__)
        httpd = wsgiref.simple_server.make_server(listen_address, listen_port, opds_root)
        httpd.serve_forever()


if __name__ == "__main__":
    sys.exit(main())


