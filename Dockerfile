FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /VJ-Forward-Bot

COPY requirements.txt .

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -U -r requirements.txt

COPY . .

CMD gunicorn app:app & python3 main.py


# FROM python:3.10.8-slim-buster

# # Replace invalid apt URLs with archive ones
# RUN sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g' /etc/apt/sources.list && \
#     sed -i 's|http://security.debian.org/debian-security|http://archive.debian.org/debian-security|g' /etc/apt/sources.list && \
#     apt update && apt upgrade -y && \
#     apt install git -y

# COPY requirements.txt /requirements.txt

# RUN pip3 install -U pip && pip3 install -U -r /requirements.txt
# RUN mkdir /VJ-Forward-Bot
# WORKDIR /VJ-Forward-Bot
# COPY . /VJ-Forward-Bot
# CMD gunicorn app:app & python3 main.py
