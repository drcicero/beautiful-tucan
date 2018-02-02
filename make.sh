#! /bin/sh

python3 vv_flatten.py 2017-11-07-ws1718-bsc.json "WS17/18 · BSc Informatik" \
  "Liste der Kurse im Wintersemester 2017/2018 für Studierende im Studiengang 'Bachelor of Science Informatik' an der TU Darmstadt (in der Prüfungsordnung von 2009)" > gh-pages/po09-bsc-1718.html

python3 vv_flatten.py 2017-11-07-ws1718-msc.json "WS17/18 · MSc Informatik" \
  "Liste der Kurse im Wintersemester 2017/2018 für Studierende im Studiengang 'Master of Science Informatik' an der TU Darmstadt (in der Prüfungsordnung von 2015)" > gh-pages/po15-msc-1718.html

python3 vv_flatten.py complete.json "WS17/18 · Informatik" \
  "Liste der Kurse im Wintersemester 2017/2018 für Studierende der Informatik an der TU Darmstadt (in der Prüfungsordnung von 2015)" > gh-pages/po15-1718.html

cp code.js gh-pages/code.js
