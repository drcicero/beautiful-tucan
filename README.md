# RUN


 *  Install mechanicalsoup, bs4, pystache and mypy as dependencies:

    ~~~
    $ pip3 install --user -q mechanicalsoup pystache mypy
    ~~~

 *  Download data from tucan and inferno into a directory called 'cache', and
    create html+js+css files in a directory called 'gh-pages'.

    ~~~
    $ TUID_USER=xxyyxxxx TUID_PASS=xxxxxxxxxxxx sh make.sh
    ~~~

 *  Now copy the contents of gh-pages to a directory that is served by a webserver,
    for example via cp or rsync:

    ~~~
    $ cp -v -r gh-pages/* ~/.public_html/beautiful-tucan/
    ~~~

## Docker

Alternatively, it is also possible to perform build and run using Docker:

~~~
docker build -t beautiful-tucan -f Dockerfile .
docker run --rm -e TUID_USER=<TU_USER> -e TUID_PASS=<TU_PASSWORD> -v <OUTPUT_PATH>:/dist beautiful-tucan
~~~

## moment.js
If you want to use moment.js to generate ical files instead of just string manipulation,
run before doing anything:

~~~
$ npm install
$ npm run init
~~~

Or use the npm.Dockerfile.

~~~
docker build -t beautiful-tucan -f npm.Dockerfile .
docker run --rm -e TUID_USER=<TU_USER> -e TUID_PASS=<TU_PASSWORD> -v <OUTPUT_PATH>:/dist beautiful-tucan
~~~


# LICENCE

This code is based on tucan-crawler by davidgengenbach, which is GPL licenced.
Because our code is based on GPL licenced code, this code is also GPL licenced.

Dependencies:
* mechanicalsoup is MIT licenced.
* pystache is MIT licenced.
* python / mypy is Python Software Foundation License (PSF).
