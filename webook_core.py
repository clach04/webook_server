
import bisect
import json
import logging
import os
import tempfile


log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(level=logging.INFO)


ebook_only_mimetypes = {
    'cbr': 'application/x-cbr',  # application/vnd.comicbook-rar
    'cbt': 'application/vnd.comicbook+tar',
    'cb7': 'application/x-7z-compressed',
    'cbz': 'application/x-cbz',  # application/vnd.comicbook+zip
    'epub': 'application/epub+zip',
    'epub3': 'application/epub+zip',
    'fb2': 'text/fb2+xml',  # application/fb2
    'fb3': 'text/fb3',
    'mobi': 'application/x-mobipocket-ebook',
    'txt': 'text/plain',
    'rtf': 'application/rtf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'chm': 'application/vnd.ms-htmlhelp',

    'pdb': 'application/vnd.palm',
    'prc': 'application/vnd.palm',

    'azw': 'application/vnd.amazon.ebook',
    'kf7': 'application/vnd.amazon.ebook',
    'azw3': 'application/vnd.amazon.mobi8-ebook',  # application/x-mobi8-ebook
    'kfx': 'application/vnd.amazon.mobi8-ebook',
    'azw8': 'application/vnd.amazon.mobi8-ebook',

    # UNTESTED
    'djv': 'image/vnd.djvu',
    'djvu': 'image/vnd.djvu',  # application/djvu image/x-djvu

    'htm': 'text/html',
    'html': 'text/html',
    'pdf': 'application/pdf',
    'xhtml': 'application/xhtml+xml',

    # Images
    'gif': 'image/gif',
    'j2k': 'image/jp2',
    'jp2': 'image/jp2',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'svg': 'image/svg+xml',
    'tif': 'image/tiff',
    'tiff': 'image/tiff',
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
    def base_filename(self):
        """Filename only, no path. Returns string.
        """
        filename = os.path.basename(self.filename)
        return filename

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
        filename = os.path.basename(self.filename)
        title = os.path.splitext(filename)[0]  # ignore file extension, as some clients (KoReader) use this as filename based and then add on file type as extension
        return title

    @property
    def file_extension(self):
        """Guess book file extension (likely not a guess) based on filename (rather than content). Returns string.
        """
        filename = os.path.basename(self.filename)
        result = os.path.splitext(filename)[1]
        return result

    @property
    def file_octet_size(self):
        """Lookup size in bytes on disk. Returns integer.
        NOTE does (uncached) lookup each time, individually (no batch)
        """
        result = os.path.getsize(self.filename)
        return result


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
    config['ebook_dir'] = os.path.abspath(config['ebook_dir'])
    config['self_url_path'] = os.environ.get('WEBOOK_SELF_URL_PATH', config.get('self_url_path', None))  # if this is not set, OPDS cannot proceed - not safe to default as koreader will silently fail with BAD urls for metadata lookup
    config['temp_dir'] = config.get('temp_dir', os.environ.get('TEMP', tempfile.gettempdir()))

    return config

# Local file system navigation functions
def walker(directory_name, process_file_function=None, process_dir_function=None, extra_params_dict=None):
    """extra_params_dict optional dict to be passed into process_file_function() and process_dir_function()

    def process_file_function(full_path, extra_params_dict=None)
        extra_params_dict = extra_params_dict or {}
    """
    extra_params_dict or {}
    # TODO scandir instead... would be faster - but for py2.7 requires external lib
    for root, subdirs, files in os.walk(directory_name):
        if process_file_function:
            for filepath in files:
                full_path = os.path.join(root,filepath)
                process_file_function(full_path, extra_params_dict=extra_params_dict)
        if process_dir_function:
            for sub in subdirs:
                full_path = os.path.join(root, sub)
                process_dir_function(full_path, extra_params_dict=extra_params_dict)

def recent_files_filter(full_path, extra_params_dict=None):
    max_recent_files = extra_params_dict['max_recent_files']
    recent_files = extra_params_dict['recent_files']
    mtime = int(os.path.getmtime(full_path))
    list_value = (mtime, full_path)
    do_insert = False
    if len(recent_files) < max_recent_files:
        do_insert = True
    elif recent_files:
        oldest_entry = recent_files[0]
        if list_value > oldest_entry:
            do_insert = True
    if do_insert:
        position = bisect.bisect(recent_files, (mtime, full_path))
        bisect.insort(recent_files, (mtime, full_path))
        if len(recent_files) > max_recent_files:
            del recent_files[0]

ORDER_ASCENDING = 'ascending'
ORDER_DESCENDING = 'descending'
def find_recent_files(test_path, number_of_files=20, order=ORDER_ASCENDING):
    extra_params_dict = {
        #'directory_path': directory_path,  # not used
        #'directory_path_len': directory_path_len,
        'max_recent_files': number_of_files,
        'recent_files': [],
    }

    walker(test_path, process_file_function=recent_files_filter, extra_params_dict=extra_params_dict)
    recent_files = extra_params_dict['recent_files']
    if ORDER_DESCENDING == order:
        recent_files.reverse()
    for mtime, filename in recent_files:
        yield filename
