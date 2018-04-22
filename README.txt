################################################################################
# SETUP

Install dependencies either via apt (on debian/ubuntu/... based platforms).
$ apt install python3 python3-mechanicalsoup python3-bs4 python3-pystache

Or via pip3
$ pip3 install --user mechanicalsoup bs4 pystache

If you have neither pip nor apt, but you got python via 'conda', you may be able use
$ conda install pystache mechanicalsoup bs4
but i never tried that!


################################################################################
# RUN

$ sh make.sh
TUID_USER: [TUID]
TUID_PASS: [PASSWORD]

This will download some data into a directory called 'cache',
and create some html, js and css files in a directory called 'gh-pages'.


################################################################################
# LICENCE

Dependencies:
* bs4 (beautifulsoup) is MIT licenced.
* mechanicalsoup is MIT licenced.
* pystache is MIT licence.

This code is based on tucan-crawler by davidgengenbach, which is GPL licenced.

Because our code is based on GPL licenced code, this code is also GPL licenced.

TODO: Add GPL licence file.
