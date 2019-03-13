#! /bin/sh

export LANG=de_DE.UTF-8

today="$(date --rfc-3339=date)"
echo $today

#pip3 install --user -q mechanicalsoup bs4 pystache
[ -d cache/"$today" ] || rm cache/*.*    # new day delete cache

mkdir -p cache    cache/"$today"      && # create folders
mkdir -p gh-pages gh-pages/"$today"   &&
python3 step1.py                      && # download
  cp cache/*.* cache/"$today"         && # backup
python3 step2.py                      && # generate
  cp gh-pages/*.* gh-pages/"$today"   && # backup
echo success
