
import json
import logging
import os


log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(level=logging.INFO)


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


def load_config(config_filename):
    log.info('Attempt to load config file %r', config_filename)

    f = open(config_filename, 'rb')
    data = f.read()
    data = data.decode('utf-8')
    f.close()

    config = json.loads(data)

    default_net_config = {
        'debug': False,
        'port': int(os.environ.get('LISTEN_PORT', 8080)),
        'host': os.environ.get('LISTEN_ADDRESS', '0.0.0.0'),  # '127.0.0.1',
    }
    default_net_config.update(config.get('config', {}))
    config['config'] = default_net_config
    config['config']['port'] = int(os.environ.get('LISTEN_PORT', config['config']['port']))  # FIXME this override is more complicated than it should be
    config['config']['host'] = os.environ.get('LISTEN_ADDRESS', config['config']['host'])  # FIXME this override is more complicated than it should be
    config['ebook_dir'] = os.environ.get('EBOOK_DIR', config.get('ebook_dir', os.path.abspath('books')))
    config['self_url_path'] = os.environ.get('WEBOOK_SELF_URL_PATH', config.get('self_url_path', None))  # if this is not set, OPDS cannot proceed - not safe to default as koreader will silently fail with BAD urls for metadata lookup

    return config
