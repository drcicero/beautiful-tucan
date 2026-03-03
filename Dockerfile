FROM python:3.10-slim

WORKDIR /beautiful-tucan

RUN pip install mechanicalsoup pystache mypy sqlite_dbm

COPY make.sh step1.py step2.py utils.py page.html index.html style.css code.common.js code.orig.js ./

CMD sh -c "ls -la cache; sh make.sh"
