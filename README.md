# RUN

~~~
$ git clone --depth 1 https://github.com/drcicero/beautiful-tucan.git
$ cd beautiful-tucan
$ pip3 install --user -q mechanicalsoup bs4 pystache
$ sh make.sh
TUID_USER: xxyyxxxx
TUID_PASS: xxxxxxxxxxxxxxxxx
~~~

This will install mechanicalsoup, bs4 and pystache as dependencies,
download data from tucan and inferno into a directory called 'cache', and
create html+js+css files in a directory called 'gh-pages'.

Now copy the contents of gh-pages to a directory that is served by a webserver,
for example via cp or rsync:
~~~
$ cp -v -r gh-pages/* ~/.public_html/beautiful-tucan/
~~~

# LICENCE

Dependencies:
* bs4 (beautifulsoup) is MIT licenced.
* mechanicalsoup is MIT licenced.
* pystache is MIT licenced.

This code is based on tucan-crawler by davidgengenbach, which is GPL licenced.

Because our code is based on GPL licenced code, this code is also GPL licenced.
