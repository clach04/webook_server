#!/usr/bin/env python

import datetime
import json
import logging
import os
import os.path
import sys
import tempfile
from time import sleep
import time


import flask
from flask import Flask, abort, request

# Optional Sentry support
try:
    if os.environ.get('SENTRY_DSN') is None:
        raise ImportError
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    # dsn param to sentry_sdk.init() can be ommited if SENTRY_DSN environment variable is set
    def sentry_init():
        log.error('clach04 entry')
        sentry_sdk.init(
            integrations=[FlaskIntegration()]
        )
        sentry_sdk.capture_message('Starting')
except ImportError:
    def sentry_init():
        log.error('sentry_init() called without SENTRY_DSN or sentry_sdk')
        pass


import ebook_conversion


version_tuple = (0, 0, 1)
version = version_string = __version__ = '%d.%d.%d' % version_tuple
__author__ = 'clach04'

is_win = (sys.platform == 'win32')

log = logging.getLogger(__name__)
logging.basicConfig()  # TODO include function name/line numbers in log
log.setLevel(level=logging.DEBUG)  # Debug hack!

log.info('Python %s on %s', sys.version, sys.platform)
log.info('Flask %s', flask.__version__)
log.info('ebook_conversion %s', ebook_conversion.convert_version())

TEMP_DIR = os.environ.get('TEMP', tempfile.gettempdir())

dump_json = json.dumps
load_json = json.loads

ebook_only_mimetypes = {
    'epub': 'application/epub+zip',
    'mobi': 'application/x-mobipocket-ebook',
    'txt': 'text/plain',  # or;  is the default value for all other cases. An unknown file type 
}

app = Flask(__name__)

## DEBUG dev hack for browser testing!
"""
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response
"""


@app.route("/")
def hello():
    return '<a href="mobi/">mobi/</a>'
    # TODO loop through ebook_only_mimetypes and list links

@app.route("/<path:url_path>")
def any_path(url_path):
    log.info('path %s', url_path)
    ebook_format_split = url_path.split('/', 1)
    log.info('ebook_format _split %s', ebook_format_split)
    if ebook_format_split:
        ebook_format = ebook_format_split[0]
        ebook_format = ebook_format.lower()
        del(ebook_format_split[0])
        if ebook_format_split:
            directory_path = ebook_format_split[0]
        else:
            directory_path = None
    else:
        abort(404)
    log.info('ebook_format %s', ebook_format)
    log.info('directory_path %s', directory_path)
    if directory_path:
        directory_path = os.path.normpath(directory_path)
        directory_path = os.path.join(config['ebook_dir'], directory_path)
    else:
        directory_path = config['ebook_dir']
    log.info('directory_path %s', directory_path)
    if os.path.isfile(directory_path):
        # do conversion
        # TODO if ebook_format is 'file'/'raw'/etc. always serve raw file and/or offer dialog for viewing/changing meta data in the generated download
        # TODO if file already in expected formatting serve raw file
        # TODO consider file caching (see note below about deleting/cleanup of temp files)
        log.info('convert ebook from %s into %s', directory_path, ebook_format)
        # TODO if same format, do not convert
        # TODO use meta data in file to generate filename
        #result_ebook_filename = 'fixme_generate_filename.' + ebook_format
        result_ebook_filename =  os.path.basename(directory_path)
        result_ebook_filename = os.path.splitext(result_ebook_filename)[0] + '.' + ebook_format
        tmp_ebook_filename = 'fixme_generate_filename.' + ebook_format
        tmp_ebook_filename = os.path.join(config['temp_dir'], tmp_ebook_filename)
        ebook_conversion.convert(directory_path, tmp_ebook_filename)
        # now serve content of tmp_ebook_filename, then delete tmp_ebook_filename
        mimetype_str = ebook_only_mimetypes[ebook_format]
        """
        f = open(tmp_ebook_filename, 'rb')
        data = f.read()  # read the entire thing... can I feed file object as the response?
        f.close()
        resp = flask.Response(response=data,
                        status=200,
                        mimetype=mimetype_str)
        resp.headers['X-Content-Type-Options'] = 'nosniff'  # direct browser to NOT sniff the mimetype, i.e. do not guess
        return resp
        """
        # TODO add flask.__version__.split('.') conditional check
        #return flask.send_file(tmp_ebook_filename, mimetype=mimetype_str, download_name=result_ebook_filename, as_attachment=True)  # flask 2.0
        return flask.send_file(tmp_ebook_filename, mimetype=mimetype_str, attachment_filename=result_ebook_filename, as_attachment=True)  # example; '0.12.2' pre flask 2.0
    elif os.path.isdir(directory_path):
        # do browse
        # FIXME TODO if missing trailing '/' end up with parent directory...
        log.info('browse %s', directory_path)
        # format vaugely like Apache and Nginx file browse / auto-index mode
        # TODO use a template
        HTML_HEADER = """<html><head><title>Index of {path_title}</title></head><body bgcolor="white"><h1>Index of {path_title}</h1><hr><pre><a href="../">../</a>\n"""
        HTML_FOOTER = "</pre><hr></body></html>"
        path_title = url_path
        os_path = directory_path
        html = HTML_HEADER.format(path_title=path_title)
        files = os.listdir(os_path)
        for filename in files:
            file_path = os_path+'/'+filename
            size = str(os.path.getsize(file_path))
            date = os.path.getmtime(file_path)
            date = time.gmtime(date)
            date = time.strftime('%d-%b-%Y %H:%M',date)  # match Apache/Nginix date format (todo option for ISO)
            spaces1 = ' '*(50-len(filename))
            spaces2 = ' '*(20-len(size))
            # FIXME cgi escape needed!
            if os.path.isdir(file_path): html += '<a href="' + filename + '/">' + filename + '/</a>'+spaces1+date+spaces2+'   -\n'
            else: html += '<a href="' + filename + '">' + filename + '</a>'+spaces1+' '+date+spaces2+size+'\n'
        html += HTML_FOOTER
        response_headers = {'Content-Type': 'text/html','Content-Length': str(len(html))}
        response = flask.Response(html, status='200 OK', headers=response_headers)
        return response
    else:
        raise NotImplementedError('unknown file stat')
    abort(404)


if __name__ == "__main__":
    argv = sys.argv

    try:
        config_filename = argv[1]
    except IndexError:
        config_filename = 'config.json'
    log.info('Using config file %r', config_filename)

    f = open(config_filename, 'rb')
    data = f.read()
    data = data.decode('utf-8')
    f.close()

    config = load_json(data)

    cert_path, key_path = '', ''
    default_config = {
        'debug': False,
        'port': 8080,
        'host': '127.0.0.1',
        #'ssl_context': 'adhoc'
        #'ssl_context': (cert_path, key_path)
    }
    default_config.update(config.get('config', {}))
    config['config'] = default_config

    settings = config['config']
    # dumb "comment" support, remove any keys that start with a "#"
    for key in list(settings.keys()):
        if key.startswith('#'):
            del(config['config'][key])
    protocol = 'http'
    if settings.get('ssl_context'):
        protocol = 'https'
        ssl_context = settings['ssl_context']
        if ssl_context != 'adhoc':
            settings['ssl_context'] = (ssl_context[0], ssl_context[1])
    sentry_init()
    log.info('Serving on %s://%s:%d', protocol, settings['host'], settings['port'])
    config['ebook_dir'] = os.path.abspath(config.get('ebook_dir', '.'))
    log.info('using ebook directory ebook_dir: %s', config['ebook_dir'])
    config['temp_dir'] = config.get('temp_dir', TEMP_DIR)
    log.info('using temporary directory temp_dir: %s', config['temp_dir'])
    app.run(**settings)
