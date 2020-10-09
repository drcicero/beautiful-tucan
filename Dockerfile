FROM node:14-alpine

COPY . /beautiful-tucan

RUN cd beautiful-tucan \
    && npm install \
    && npm run init


FROM python:3.7-slim

COPY . /beautiful-tucan
COPY --from=0 /beautiful-tucan/dist /beautiful-tucan/dist

WORKDIR /beautiful-tucan

RUN pip install mechanicalsoup pystache mypy

CMD sh make.sh && cp -r gh-pages/* /dist