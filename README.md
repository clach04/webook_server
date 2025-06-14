-*- coding: utf-8 -*-

# webook_server - Worst E-book server

Home page https://github.com/clach04/webook_server

## Table Of Contents
  * [Overview](#overview)
    + [Features](#features)
  * [Alternatives](#alternatives)
  * [Getting Started](#getting-started)
    + [Debian/Ubuntu install dependencies](#debian-ubuntu-install-dependencies)
    + [Python install dependencies](#python-install-dependencies)
    + [Run](#run)
    + [Sample Run](#sample-run)
  * [systemd webook service](#systemd-webook-service)
  * [Notes and config](#notes-and-config)
    + [json config file](#json-config-file)
    + [Operating System Environment Variables](#operating-system-environment-variables)
    + [https / TLS / SSL support](#https---tls---ssl-support)
  * [Known working environments](#known-working-environments)
    + [Debian / Ubuntu / Armbian](#debian---ubuntu---armbian)
    + [Debian GNU/Linux 9 (stretch)](#debian-gnu-linux-9--stretch-)
    + [Microsoft Windows](#microsoft-windows)
    + [cURL client](#curl-client)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>


## Overview

This is either:

  * 🏴󠁧󠁢󠁳󠁣󠁴󠁿 The [wee](https://dictionary.cambridge.org/us/dictionary/english/wee) book server
  * 💩📖 The worst  ebook conversion server

Basic ebook server that doesn't require a database.

Given a directory of (possibly directories of) ebooks serve a web (http) interface of the files and automatically convert to the desired format (incomplete examples; mobi, epub, fb2, html, txt, rtf, etc.). The format is specified in the URL and browsing is supported. This works great with a web browser (including the Amazon Kindle Experimental Web Browser) and [OPDS](https://en.m.wikipedia.org/wiki/Open_Publication_Distribution_System) client like [KOReader](https://github.com/koreader/koreader).

### Features

  * Serve directory of ebooks to either a web browser or an OPDS client
      * Base bones [OPDS Spec support](https://specs.opds.io/opds-1.2) - does not pretend to be complete, it implements enough for my basic usage at home
  * Simple search support for both web browser and OPDS client/readers
      * Search for recently added files/books
      * Search is case insensitive (single term) partial match support (i.e. no regex support) for path names and directories
      * Example; `book` would match a file named "mybook.txt" and a directory called "books"
  * OPTIONAL - Ebook Conversion support (currently via Calibre ebook convert tool)
  * OPDS support has no dependencies outside of Python stdlib BUT will make use of addition WSGI servers if available
      * Tested clients; KOReader (Android and Kindle), AlReader (Android), AlReaderX (Android), FBReader (Android, FBReader Premium (Android)
      * does **not** support ebook metadata (including covers/thumbails)
      * does **not** support OPDS Page Streaming Extension
 * Web browser support (Native Kindle (experimental) web browser, Mozilla Firefox, Google Chrome, Microsoft Edge, Elink, Lynx, etc.) as well as OPDS clients
  * Works with Python 3.x and 2.6+


Comes with:

  * webook_opds_server.py is for **both** web browsers (e.g. the Kindle web browser) and OPDS clients like:
      * https://github.com/koreader/koreader
      * http://alreader.kms.ru/
      * https://fbreader.org/
  * webook_server.py (deprecated and only available in old legacy branch https://github.com/clach04/webook_server/tree/legacy_flask) is ONLY for web browsers (e.g. the Kindle web browser)

## Alternatives

The closest equivilents of this tool are [KindleGate](https://github.com/hzengin/KindleGate) which **only** supports conversion to mobi and https://github.com/dubyte/dir2opds.

Also take a look at:

  * Other Tools [doc similar ebook tools](https://github.com/clach04/webook_server/issues/9) has a much larger list
  * https://github.com/seblucas/cops - requires calibre2opds
  * https://github.com/calibre2opds/calibre2opds
  * https://github.com/dubyte/dir2opds
      * https://github.com/clach04/dir2opds/wiki
      * https://github.com/clach04/dir2opds/wiki/Tested-Clients


## Getting Started

Either use Operating System packages or Python packages

### Debian/Ubuntu install dependencies

For Python 2.x deployment:

    sudo apt install calibre

For Python 3.x deployment (with calibre ebook-convert exe - likely Python2):

    sudo apt install calibre


### Python install dependencies

NOTE Currently relies on [Calibre](https://github.com/kovidgoyal/calibre) ebook-convert (not documented in the Python dependency install notes below).

ONLY needed for the web browser version, not needed for OPDS

If installing/working with a source checkout issue:

    pip install -r requirements.txt

### Run

    cp example_config.json config.json
    # Optional; edit config.json with "ebook_dir" (defaults to ./ if omitted) and "temp_dir" (will use OS environment variable TEMP if omitted, if that's missing system temp location) location
    python webook_opds_server.py
    py -3 webook_opds_server.py -g example_config.json

Then open a browser to http://localhost:8080/... or issue:

    curl http://localhost:8080/
    curl http://localhost:8080/recent?n=10
    curl http://localhost:8080/file
    curl http://localhost:8080/....

### Sample Run

1. Download the sample_reading_media.zip from https://github.com/clach04/sample_reading_media/releases/tag/v0.1
2. Extract to local directory, ideally into a directory called `sample_reading_media`
3. Create a (or edit existing) config file, for example named `sample_reading_media.json`

        {
            "ebook_dir": "sample_reading_media"
        }

if setting tmp dir, mkdir -p /tmp/ebookserver/....

4. Run the server with the config file:

        python webook_opds_server.py sample_reading_media.json

5. Open Web browser to http://127.0.0.1:8080/ and browse around, for example download

      * http://127.0.0.1:8080/mobi/test_book_fb2.fb2 which will convert a FictionBook to Mobi format
      * http://127.0.0.1:8080/epub/test_book_fb2.fb2 which will convert a FictionBook to epub format (same book as above)
      * http://127.0.0.1:8080/file/test_book_fb2.fb2 and http://127.0.0.1:8080/fb2/test_book_fb2.fb2 which will download without conversion

## systemd webook service

Systemd service (e.g. for Raspbian).

For more information see:

  * https://www.raspberrypi.org/documentation/linux/usage/systemd.md
  * https://coreos.com/os/docs/latest/using-environment-variables-in-systemd-units.html

NOTE directory name for `ExecStart` and `WorkingDirectory` in `webook.service`.

Install

    # Potententially edit service; ExecStart, WorkingDirectory, User
    # Review config file
    sudo cp scripts/webook.service /etc/systemd/system/webook.service
    sudo chmod 644 /etc/systemd/system/webook.service
    sudo systemctl enable webook.service

Usage

    sudo systemctl stop webook.service
    sudo systemctl start webook.service
    sudo systemctl restart webook.service
    sudo systemctl status webook.service  # status and recent logs
    sudo systemctl status webook.service -n 100  # show last 100 log entries
    journalctl  -u webook.service  # show all logs

    systemctl list-unit-files --state=enabled | grep webook

NOTE if changing service files, e.g. adding `Environment`, restart config (not just specific service):

    sudo systemctl daemon-reload
    sudo systemctl restart webook.service

## Notes and config

### json config file

  * config for web server config
  * ebook_dir - directory to serve, if omitted defaults to current directory (`./`)
  * temp_dir - temporary location on disk to store generated files. Will use OS environment variable TEMP if
 omitted, if that's missing system temp location. NOTE recommend using a temporary file system, on devices like RaspberryPi and SBCs with SD Cards, recommend using directory that is NOT located on SD Card to preserve card
 * self_url_path - for OPDS server, this is the public http / https address of the server and is required for search to work correctly (when behind a reverse proxy). Example `http://123.45.67.89:8080`

### Operating System Environment Variables

  * CALIBRE_EBOOK_CONVERT_EXE - full path to ebook-convert exe (if not using Calibre as a library). For Windows do NOT set with double quotes, even for paths with spaces
  * USE_CALIBRE_EBOOK_CONVERT_EXE - if set forces the use of ebook-convert exe (that is, do not use Calibre as a library)
  * TEMP - override for temp disk location, see `temp_dir` in json config
  * EBOOK_DIR - override for ebook location, see `ebook_dir` in json config
  * SENTRY_DSN - optional Sentry token - NOT applicable to OPDS server
  * LISTEN_PORT - OPDS override for config file `config.port`
  * LISTEN_ADDRESS - OPDS override for config file `config.host`

### https / TLS / SSL support

  * There is no https support for the OPDS server.
  * There is no authentication/authorization support
  * Recommendation is to use a reverse proxy (with authentication).

## Known working environments

Known to work under Linux with

### Debian / Ubuntu / Armbian

DISTRIB_DESCRIPTION="Ubuntu 20.04.3 LTS"
NAME="Ubuntu"
VERSION="20.04.3 LTS (Focal Fossa)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Armbian 21.08.6 Focal"
VERSION_ID="20.04"

  * Python 3.8.10 (default, Mar 15 2022, 12:22:08)
      * ebook_conversion calibre_4.99.4


### Debian GNU/Linux 9 (stretch)

With:

  * Python 2.7.13 (default, Aug 22 2020, 10:03:02)
      * ebook_conversion calibre_2.75.1
  * Python 3.5.3 (default, Sep 27 2018, 17:25:39)
      * calibre ebook-convert exe version 2.75.1

Using the OS packages for Python and Calibre.

### Microsoft Windows

  * Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)] on win32
      * calibre ebook-convert exe version 4.2.0

### cURL client

For testing. By default cURL will be detected by webook_opds_server.py
as an OPDS client (rather than as a web browser), this can be influenced
via the http accept header.

    curl -v --header "ACCEPT: */*"  # act as an OPDS client - NOTE this happens to be the default so this is not actually needed
    curl -v --header "ACCEPT: text/html"  # convince OPDS server this client is a web browser

    WEBOOK_SERVER_URL=http://localhost:9987
    WEBOOK_SERVER_URL=http://localhost:8080
    export WEBOOK_SERVER_URL


    curl ${WEBOOK_SERVER_URL}
    curl -v --header "ACCEPT: text/html" ${WEBOOK_SERVER_URL}  # convince OPDS server this client is a web browser

    curl ${WEBOOK_SERVER_URL}/search?q=foundation
    curl -v --header "ACCEPT: text/html" ${WEBOOK_SERVER_URL}/search?q=foundation  # still a web browser html search due to URL

    curl -v --header "ACCEPT: text/html" ${WEBOOK_SERVER_URL}/opds/search?q=foundation  # OPDS search and results
    curl -v ${WEBOOK_SERVER_URL}/opds/search?q=foundation  # OPDS search and results


    # OPDS file browse
    curl -v  ${WEBOOK_SERVER_URL}/file/
