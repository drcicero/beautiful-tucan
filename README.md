# RUN

~~~
$ git clone --depth 1 https://github.com/drcicero/beautiful-tucan.git
$ cd beautiful-tucan
$ env TUID_USER=xx11xxxx TUID_PASS=xxxxxxxxxx sh make.sh
~~~

This will invoke 'pip3 install mechanicalsoup bs4 pystache' to get dependencies,
download data from tucan and inferno into a directory called 'cache', and
create html+js+css files in a directory called 'gh-pages'.

Now copy the contents of gh-pages to a directory that is served by a webserver:
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

TODO: Add GPL licence file.
