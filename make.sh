#! /bin/sh

mkdir gh-pages
python3 step1.py # download
python3 step2.py # generate
cp code.js gh-pages/code.js

