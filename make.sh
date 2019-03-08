#! /bin/sh

export LANG=de_DE.UTF-8

today="$(date --rfc-3339=date)"

mkdir -p gh-pages gh-pages/"$today"         &&
pip3 install --user -q mechanicalsoup bs4 pystache &&
python3 step1.py                            && # download
python3 step2.py                            && # generate
cp gh-pages/*.* gh-pages/"$today"           && # backup
echo success

