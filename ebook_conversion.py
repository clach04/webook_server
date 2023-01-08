"""Wrapper arond Calibre ebook conversion

1) as lib, wrapper functions around calibre
2) as exe wrapper for ebook-convert

All implementations rely on temp disk space and will spool to disk.
"""

import logging
import os
import sys


log = logging.getLogger(__name__)
logging.basicConfig()  # TODO include timestamp - and maybe function name/line numbers in log
log.setLevel(level=logging.DEBUG)  # Debug hack!


"""Boiler plate from /usr/bin/ebook-convert
"""

path = os.environ.get('CALIBRE_PYTHON_PATH', '/usr/lib/calibre')
if path not in sys.path:
    sys.path.insert(0, path)

sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', '/usr/share/calibre')
sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', '/usr/lib/calibre/calibre/plugins')
sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', '/usr/bin')


try:
    if os.environ.get('USE_CALIBRE_EBOOK_CONVERT_EXE'):
        log.info('USE_CALIBRE_EBOOK_CONVERT_EXE is set, only use EXE not library mode')
        raise ImportError

    import calibre
    from calibre.ebooks.conversion.cli import main as calibre_ebook_convert
except ImportError:
    calibre = None
    import subprocess


# Wrapper functions
if calibre:
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
