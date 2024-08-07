FROM python:3.9-slim-buster

RUN apt-get update -qq && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends build-essential cron python3-dev curl iputils-ping default-mysql-client pkg-config libmariadb-dev libhdf5-dev locales vim-tiny
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8

RUN useradd -ms /bin/bash -u 33 -g 33 www-data

RUN mkdir -p /nextseek/logs

WORKDIR /nextseek

COPY . .

USER www-data

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

USER root

RUN chown -R www-data:www-data /nextseek
RUN chmod +x docker/entrypoint.sh

USER www-data

CMD ["docker/entrypoint.sh"]
