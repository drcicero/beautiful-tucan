#! /bin/sh

python3 vv_flatten.py 2017-11-07-ws1718-bsc.json "TUDA VV WS17/18 · BSc Informatik PO'09" > ~/Downloads/tucan-bsc-1718.html
python3 vv_flatten.py 2017-11-07-ws1718-msc.json "TUDA VV WS17/18 · MSc Informatik PO'15" > ~/Downloads/tucan-msc-1718.html
python3 vv_flatten.py complete.json "TUDA VV WS17/18 · BSc Informatik PO'15" > ~/Downloads/tucan-complete-1718.html
