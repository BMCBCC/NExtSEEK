#!/bin/bash

python3 manage.py crontab add
python3 -m gunicorn dmac.wsgi
