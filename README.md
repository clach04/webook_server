# webook_server - Worst E-book server

The worst  ebook conversion server.

Given a directory of (possibly directories of) ebooks serve a web (http) interface of the files and automatically convert to the desired format (incomplete examples; mobi, epub, fb2, html, txt, rtf, etc.). The format is specified in the URL and browsing is supported. This works great with a web browser (including the Amazon Kindle Experimental Web Browser) and [KOReader](https://github.com/koreader/koreader).

The closest equivilent of this tool is [KindleGate](https://github.com/hzengin/KindleGate) which **only** supports conversion to mobi.

As of now this is **not** an OPDS server, if you are looking for one, take a look at:

  * https://github.com/seblucas/cops - requires calibre2opds
  * https://github.com/calibre2opds/calibre2opds
  * https://github.com/dubyte/dir2opds


## Getting Started

Either use Operating System packages or Python packages

### Debian/Ubuntu install dependencies

	sudo apt install calibre python-flask


### Python install dependencies

NOTE Currently relies on [Calibre](https://github.com/kovidgoyal/calibre) ebook-convert (not documented in the Python dependency install notes below).

If installing/working with a source checkout issue:

    pip install -r requirements.txt

Run:

    cp example_config.json config.json
    # Optional; edit config.json with "ebook_dir" and "temp_dir" location
    python webook_server.py

Then open a browser to http://localhost:8080/... or issue:

    curl http://localhost:8080/....

## https / TLS / SSL support

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

