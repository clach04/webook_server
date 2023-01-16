"""Wrapper arond Calibre ebook conversion

1) as lib, wrapper functions around calibre
2) as exe wrapper for ebook-convert

All implementations rely on temp disk space and will spool to disk.
"""

import logging
import os
import shutil
import sys
import tempfile


log = logging.getLogger(__name__)
logging.basicConfig()  # TODO include timestamp - and maybe function name/line numbers in log
log.setLevel(level=logging.DEBUG)  # Debug hack!

try:
    import KindleUnpack  # https://github.com/clach04/KindleUnpack
    import KindleUnpack.lib.kindleunpack

    unpack_book = KindleUnpack.lib.kindleunpack.unpackBook  # fake out a pep8 naming comvention
    os.environ['USE_CALIBRE_EBOOK_CONVERT_EXE'] = 'true'  # skip calibre import?
except ImportError:
    unpack_book = None




try:
    if os.environ.get('USE_CALIBRE_EBOOK_CONVERT_EXE'):
        log.info('USE_CALIBRE_EBOOK_CONVERT_EXE is set, only use EXE not library mode')
        raise ImportError

    """Boiler plate from /usr/bin/ebook-convert
    """

    path = os.environ.get('CALIBRE_PYTHON_PATH', '/usr/lib/calibre')
    if path not in sys.path:
        sys.path.insert(0, path)

    sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', '/usr/share/calibre')
    sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', '/usr/lib/calibre/calibre/plugins')
    sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', '/usr/bin')

    import calibre
    from calibre.ebooks.conversion.cli import main as calibre_ebook_convert
except ImportError:
    calibre = None
    import subprocess


# Wrapper functions
if unpack_book:
    # TODO source and destination conversion lookup/check support? E.g. only azw3 -> epub, mobi -> epub?
    # TODO use best conversion tool, for format-pairing with calibre as fallback?
    def convert_version():
        return 'KindleUnpack_' + getattr(KindleUnpack, '__version__', '??')

    def convert(original_filename, new_filename):
        # Faster than calibre but limited to kindle (azw3) to epub
        # TODO capture stdout/stderr? At the moment stdout/stderr is allowed to be emitted
        # NOTE uses temp disk spacel can be controlled via TMPDIR, TEMP or TMP environment variables
        log.info('KindleUnpack in-process conversion, see stdout/stderr for status')
        log.debug('%r -> %r', original_filename, new_filename)
        if not new_filename.lower().endswith('.epub'):  # TODO epub2 and epub3?
            raise NotImplementedError('output format %r, only epub supported' % new_filename)

        # should temp name include (basename of) original filename?
        temp_directory = tempfile.mkdtemp(prefix='kindleunpack__')  # be nice to use Py 3.2 tempfile.TemporaryDirectory()
        log.debug('temp_directory=%r', temp_directory)
        try:
            # TODO mutex due to global variable usage?
            os.environ['KINDLE_UNPACK_EPUB_FILENAME'] = new_filename  # hack to specify output epub file name
            # def unpackBook(infile, outdir, apnxfile=None, epubver='2', use_hd=False, dodump=False, dowriteraw=False, dosplitcombos=False):
            unpack_book(original_filename, temp_directory)
            # TODO catch ValueError for conversion issues
        finally:
            shutil.rmtree(temp_directory)
elif calibre:
    def convert_version():
        return 'calibre_' + calibre.__version__

    def convert(original_filename, new_filename):
        # This is not a fast operation, examples;
        #                   700Kb azw3 can take almost 30 secs to convertion into mobi
        # (same)    700Kb azw3 can take almost 10 secs to convertion into epub
        # TODO capture stdout/stderr? At the moment stdout/stderr is allowed to be emitted
        log.info('in-process conversion, see stdout/stderr for status')
        result = calibre_ebook_convert(['dummy', original_filename, new_filename])
        return result  # or the new_filename?
else:
    # calibre external ebook-convert binary/exe/script

    calibre__version__ = '???'
    ebook_convert_exe = os.environ.get('CALIBRE_EBOOK_CONVERT_EXE', 'ebook-convert')
    # set CALIBRE_EBOOK_CONVERT_EXE=C:\Users\clach04\Calibre Portable\Calibre\ebook-convert.exe
    # NOTE no double quotes, even though there are spaces in the path
    log.debug('ebook_convert_exe %r', ebook_convert_exe)

    process = subprocess.Popen([ebook_convert_exe, '--version'], stdout=subprocess.PIPE)  # call ebook-convert as a subprocess
    process.wait()  # wait until it finishes it work
    ebook_convert_exe_version_stdout, ebook_convert_exe_version_stderr = process.communicate()
    log.debug('ebook_convert_exe_version_stderr %r', ebook_convert_exe_version_stderr)
    log.debug('ebook_convert_exe_version_stdout %r', ebook_convert_exe_version_stdout)
    ebook_convert_exe_version_stdout = ebook_convert_exe_version_stdout.decode('utf-8')
    log.debug('ebook_convert_exe_version_stdout %r', ebook_convert_exe_version_stdout)
    calibre__version__ = ebook_convert_exe_version_stdout.split(')', 1)[0].rsplit(' ', 1)[1]

    def convert_version():
        return 'calibre-ebook-convert_' + calibre__version__

    def convert(original_filename, new_filename):
        log.info('external-process conversion, this may take some time with no status updates')
        process = subprocess.Popen([ebook_convert_exe, original_filename, new_filename], stdout=subprocess.PIPE)  # call ebook-convert as a subprocess
        process.wait()  # wait until it finishes it work
        ebook_convert_exe_convert_stdout, ebook_convert_exe_convert_stderr = process.communicate()  # get output
        log.debug('ebook_convert_exe_convert_stderr %r', ebook_convert_exe_convert_stderr)
        log.debug('ebook_convert_exe_convert_stdout %r', ebook_convert_exe_convert_stdout)
