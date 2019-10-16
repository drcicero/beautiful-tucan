#! /bin/sh

export LANG=de_DE.UTF-8

today="$(date --rfc-3339=date)"
echo $today

[ -d cache/"$today" ] || rm cache/*.*    # new day delete cache

mkdir -p cache    cache/"$today"      && # create folders
python3 step1.py                      && # download
  cp cache/*.*    cache/"$today"      && # backup

mkdir -p gh-pages gh-pages/"$today"   &&
python3 step2.py                      && # generate
  cp gh-pages/*.* gh-pages/"$today"   && # backup

echo success
