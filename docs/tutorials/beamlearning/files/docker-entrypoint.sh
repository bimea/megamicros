#!/bin/sh
# docker-entrypint.sh for for biimea/aidb:python3.10-drf3.14.0 image build
# version 1.1 - 20221220 

if [ ! -d /app/Aidb ] ; then
    echo "This is a first installation: cloning Aidb repository..."
    cd /app
    git clone git@github.com:biimea/Aidb.git
    cd Aidb/aidb
    python manage.py makemigrations
    python manage.py migrate
    python manage.py createsuperuser --noinput
    cd aidb
    echo "ALLOWED_HOSTS = ['${ALLOWED_HOSTS}']" >> settings.py
    cp settings.py settings.template.py
    echo "done"
else
    echo "Project already installed, updating from Aidb repository..."
    cd /app/Aidb
    git pull
    cd aidb
    python manage.py makemigrations
    python manage.py migrate
    echo "done"
fi

echo "exec Biimea-Aidb..."
exec python /app/Aidb/aidb/manage.py runserver 0.0.0.0:8000
