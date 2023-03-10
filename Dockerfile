FROM python:3.8-slim

COPY . /beautiful-tucan

WORKDIR /beautiful-tucan

RUN pip install mechanicalsoup pystache mypy sqlite_dbm

CMD sh make.sh && cp gh-pages/* /dist
