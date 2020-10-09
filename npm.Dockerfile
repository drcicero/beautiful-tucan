FROM node:14-alpine

COPY . /beautiful-tucan

RUN cd beautiful-tucan \
    && npm install \
    && npm run init

FROM python:3.8-slim

COPY . /beautiful-tucan
COPY --from=0 /beautiful-tucan/dist /beautiful-tucan/dist

WORKDIR /beautiful-tucan

RUN pip install mechanicalsoup pystache mypy

CMD sh make.sh && cp gh-pages/* /dist
