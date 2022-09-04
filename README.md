# webook_server - Worst E-book server

The worst  ebook conversion server.

Given a directory of (possibly directories of) ebooks serve a web (http) interface of the files and automatically convert to the desired format (incomplete examples; mobi, epub, fb2, html, txt, rtf, etc.). The format is specified in the URL and browsing is supported. This works great with a web browser (including the Amazon Kindle Experimental Web Browser) and [KOReader](https://github.com/koreader/koreader).

The closest equivilent of this tool is [KindleGate](https://github.com/hzengin/KindleGate) which **only** supports conversion to mobi.

As of now this is **not** an OPDS server, if you are looking for one, take a look at:

  * https://github.com/seblucas/cops - requires calibre2opds
  * https://github.com/calibre2opds/calibre2opds
  * https://github.com/dubyte/dir2opds
      * https://github.com/clach04/dir2opds/wiki
      * https://github.com/clach04/dir2opds/wiki/Tested-Clients


TODO add a TOC

## Getting Started

Either use Operating System packages or Python packages

### Debian/Ubuntu install dependencies

For Python 2.x deployment:

    sudo apt install calibre python-flask

For Python 3.x deployment (with calibre ebook-convert exe - likely Python2):

    sudo apt install calibre python3-flask


### Python install dependencies

NOTE Currently relies on [Calibre](https://github.com/kovidgoyal/calibre) ebook-convert (not documented in the Python dependency install notes below).

If installing/working with a source checkout issue:

    pip install -r requirements.txt

### Run

    cp example_config.json config.json
    # Optional; edit config.json with "ebook_dir" (defaults to ./ if omitted) and "temp_dir" (will use OS environment variable TEMP if omitted, if that's missing system temp location) location
    python webook_server.py

Then open a browser to http://localhost:8080/... or issue:

    curl http://localhost:8080/....

### Sample Run

1. Download the sample_reading_media.zip from https://github.com/clach04/sample_reading_media/releases/tag/v0.1
2. Extract to local directory, ideally into a directory called `sample_reading_media`
3. Create a (or edit existing) config file, for example named `sample_reading_media.json`

        {
            "ebook_dir": "sample_reading_media"
        }

4. Run the server with the config file:

        python webook_server.py sample_reading_media.json

5. Open Web browser to http://127.0.0.1:8080/ and browse around, for example download

      * http://127.0.0.1:8080/mobi/test_book_fb2.fb2 which will convert a FictionBook to Mobi format
      * http://127.0.0.1:8080/epub/test_book_fb2.fb2 which will convert a FictionBook to epub format (same book as above)
      * http://127.0.0.1:8080/file/test_book_fb2.fb2 and http://127.0.0.1:8080/fb2/test_book_fb2.fb2 which will download without conversion

## Notes and config

### json config file

  * config for web server config
  * ebook_dir - directory to serve, if omitted defaults to current directory
  * temp_dir - temporary location on disk to store generated files. Will use OS environment variable TEMP if
 omitted, if that's missing system temp location. NOTE recommend using a temporary file system, on devices like RaspberryPi and SBCs with SD Cards, recommend using directory that is NOT located on SD Card to preserve card

### Operating System Environment Variables

  * CALIBRE_EBOOK_CONVERT_EXE - full path to ebook-convert exe (if  not using Calibre as a library). For Windows do NOT set with double quotes, even for paths with spaces
  * TEMP - override for temp disk location, see `temp_dir` in json config
  * SENTRY_DSN - optional Sentry token

### https / TLS / SSL support

https support is optional. There is no authentication/authorization support, recommendation is to use a reverse proxy *but* Flask does make it easy and quick to expose over https.

NOTE https requires pyopenssl which is not installed via the requirements above.

Either install via `pip` or package manager for system, e.g.:

    sudo apt-get install python-openssl
    sudo apt-get install python3-openssl

or

    pip install pyopenssl

Edit json config file and add to the `config` section to add a Flask run setting for `ssl_context`.
Add either `adhoc` for quick and dirty testing or add certificate and key file names.

E.g. Uncomment one of the ssl_context entries:

    ....
    "config": {
        "debug": true,
        "host": "0.0.0.0",
        "port": 8080,
        "#ssl_context": "adhoc",
        "#ssl_context": ["cert.pem", "key.pem"],
    },
    ....

Example #2 requires files to exist in current directory, generated via something like:

    openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

Which will generate a certificate valid for 1 year.

## Known working environments

Known to work under Linux with

### Debian GNU/Linux 9 (stretch)

With:

  * Python 2.7.13 (default, Aug 22 2020, 10:03:02)
      * Flask 0.12.1
      * ebook_conversion calibre_2.75.1
  * Python 3.5.3 (default, Sep 27 2018, 17:25:39)
      * Flask 0.12.1
      * calibre ebook-convert exe version 2.75.1

Using the OS packages for Python, Flask, and Calibre.

### Microsoft Windows

  * Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)] on win32
      * Flask 1.1.2
      * calibre ebook-convert exe version 4.2.0
