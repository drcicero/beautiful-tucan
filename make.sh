#! /bin/sh

export LANG=de_DE.UTF-8

mkdir -p gh-pages
pip3 install -q mechanicalsoup bs4 pystache &&
python3 step1.py && # download
python3 step2.py && # generate
cp code.js gh-pages/code.js &&
cp style.css gh-pages/style.css &&
echo success

