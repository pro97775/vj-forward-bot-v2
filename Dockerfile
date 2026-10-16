FROM python:3.11-slim

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends git gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

RUN pip3 install --no-cache-dir -U pip \
    && pip3 install --no-cache-dir -U -r /requirements.txt

WORKDIR /VJ-Forward-Bot
COPY . /VJ-Forward-Bot

CMD gunicorn -b 0.0.0.0:8080 app:app & python3 main.py
