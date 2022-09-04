"""Wrapper arond Calibre ebook conversion

1) as lib, wrapper functions around calibre
2) NOT IMPLEMENTED! as exe wrapper for ebook-convert

All implementations rely on temp disk space and will spool to disk.
"""

import os
import sys


"""Boiler plate from /usr/bin/ebook-convert
"""

path = os.environ.get('CALIBRE_PYTHON_PATH', '/usr/lib/calibre')
if path not in sys.path:
    sys.path.insert(0, path)

sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', '/usr/share/calibre')
sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', '/usr/lib/calibre/calibre/plugins')
sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', '/usr/bin')


from calibre.ebooks.conversion.cli import main as calibre_ebook_convert

# Wrapper functions

def convert(original_filename, new_filename):
    # This is not a fast operation, examples;
    #                   700Kb azw3 can take almost 30 secs to convertion into mobi
    # (same)    700Kb azw3 can take almost 10 secs to convertion into epub
    # TODO capture stdout/stderr?
    result = calibre_ebook_convert(['dummy', original_filename, new_filename])
    return result  # or the new_filename?

