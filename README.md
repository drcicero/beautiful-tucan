# RUN

Clone this repo, enter repo-folder and:

~~~
$ pip3 install --user -q mechanicalsoup bs4 pystache mypy
$ npm install
$ npm run init
$ sh make.sh
TUID_USER: xxyyxxxx
TUID_PASS: xxxxxxxxxxxxxxxxx
~~~

This will install mechanicalsoup, bs4, pystache and mypy as dependencies,
download data from tucan and inferno into a directory called 'cache', and
create html+js+css files in a directory called 'gh-pages'.

Now copy the contents of gh-pages to a directory that is served by a webserver,
for example via cp or rsync:
~~~
$ cp -v -r gh-pages/* ~/.public_html/beautiful-tucan/
~~~

# LICENCE

This code is based on tucan-crawler by davidgengenbach, which is GPL licenced.
Because our code is based on GPL licenced code, this code is also GPL licenced.

Dependencies:
* bs4 (beautifulsoup) is MIT licenced.
* mechanicalsoup is MIT licenced.
* pystache is MIT licenced.
* python / mypy is Python Software Foundation License (PSF).
