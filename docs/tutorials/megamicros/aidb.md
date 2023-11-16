# Aidb database for microphones array data

*Data* tutorial aims at defining the ways you have to prepare your data for beamforming machine learning.
Two tools are available:
* *BeamAidb* a database tool where all original data file should be stored 
* *BeamAiboard* a web tool for data segmenting


## Installing  *Aidb*

*Aidb* designates the database model used for learning signals from MegaMicro antennas.
The database operates in remote server mode with a REST interface for managing requests.

Sources are available on Github at `GitHub Beamea/Aidb <https://github.com:beameo/Aidb>`_.
Several installation methods are possible:

* In single *Docker* container mode - *single application*: This is the simplest mode: the database (*sqlite*), the web server (*python*) and the python application (*Djangorest*) are running in the same container within the same Python program;
* In double or triple container mode - *multi-servers*: database (*Postgres*, *mariadb*, *mysqldb*,…), web server (*Apache*, *Ngind*,…), and Python application (*Djangorest*) run on dedicated server programs and 1, 2 or three separate containers.

### In your local machine (MacOs and Linux systems)

We suppose here you are creating a new project. 
For that, please follow the two pre-installing next steps:

* clone the repository on your local machine
* create a python virtual environment with *Django* and *Djang-Rest-Framework* installed, and also some required Python modules:

```bash
    $ > git clone git@github.com:beamea/Aidb.git
    $ > cd Aidb
    $ > virtualenv venv
    $ > source venv/bin/activate
    (venv) $ > pip install django djangorestframework djangorestframework-simplejwt django-cors-headers django-filter dj-rest-auth
    (venv) $ > pip install ffmpeg h5py
    (venv) $ > cd aidb
    (venv) $ > python manage.py makemigrations core
    (venv) $ > python manage.py migrate
    (venv) $ > python manage.py createsuperuser --email <your_email> --username admin
```

Let's note that the initial project was created with the following commands:

```bash
    (venv) $ > django-admin startproject aidb
    (venv) $ > cd aidb
    (venv) $ > django-admin startapp core
    (venv) $ > python manage.py migrate
```

With the updated configuration file ``aidb/aidb/settings.py``:

```python
    # ...
    # Access to Megamicros python code
    from sys import path
    path.insert( 0, str(BASE_DIR) + "/../../../../../Megamicros/src" )
    path.insert( 1, str(BASE_DIR) + "/../../../../../Megamicros_aidb/src" )
    # ...
    # Application definition
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django_filters',
        'rest_framework',
        'rest_framework.authtoken',
        'corsheaders',
        'dj_rest_auth',
        'core'
    ]

    # ...
    # Internationalization
    # https://docs.djangoproject.com/en/4.1/topics/i18n/
    LANGUAGE_CODE = 'en-us'
    TIME_ZONE = 'UTC'
    #TIME_ZONE = 'Europe/Paris'
    USE_I18N = True
    USE_TZ = True

    # ...
    # REST Framework parameters
    REST_FRAMEWORK = {
        #'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
        'PAGE_SIZE': 20,
        #'DATE_INPUT_FORMATS': ['%Y-%m-%d %H:%M:%S.%f', 'iso-8601'],
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework.authentication.SessionAuthentication',
            'rest_framework.authentication.TokenAuthentication',
            #'dj_rest_auth.jwt_auth.JWTCookieAuthentication'
        ),
        #'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
    }

    SWAGGER_SETTINGS = {
        'LOGIN_URL': 'login',
        'LOGOUT_URL': 'logout',
    }

    CORS_ALLOW_ALL_ORIGINS: True
    ALLOWED_HOSTS = ['your_web_site_address.fr', '127.0.0.1']

    # MQTT parameters that should be updated to local usage
    MQTT_BROKER_HOST = 'parisparc.biimea.tech'
    MQTT_BROKER_PORT = 1883
    MQTT_CLIENT_ID = 'megamicros/aidb/unknown'
    MQTT_LOG_TOPIC = MQTT_CLIENT_ID + '/log'
    MQTT_LOG_QOS = 1
```

The MQTT log part is defined in the `../core/admin.py`:

```python
    # create a MQTT client:
    mqtt_client = mqtt.MqttClient( host=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT, name=MQTT_CLIENT_ID )

    # create the Mqtt Publishing Handler, set the level and add it to the logger
    mqtt_handler = mqtt.MqttPubHandler( mqtt_client, topic=MQTT_LOG_TOPIC, qos=MQTT_LOG_QOS )
    mqtt_handler.setLevel( logging.DEBUG )
    log.addHandler( mqtt_handler )
```


Launch the database server:

```bash
    (venv) $ > python manage.py runserver
```

Your database is now ready for use.

!!! Warning

    Note that for some reasons, hdf5 (version 1.12) does not work with Mac M2 processor. 
    Instead Install the 1.8 version:

    ```bash
    $ > brew install hdf5@1.8
    $ > export HDF5_DIR=/opt/homebrew/opt/hdf5@1.8
    $ > pip install h5py
    ```

!!! warning

    Note that for other reasons hdf5 may not work on Mac Os with Python 3.11 (whatever the version you want to install 1.8, 1.10  or 1.12).
    Please install Python 3.10 for the hdf5 library to work fine.


### In a container for docker environments

An instance of the repository is the implementation of a production version of the application: its containerization and then its execution. 
Some instance-specific configuration items need to be added to the configuration file.

The container image contains the platform needed to run the application, without the application itself:

#### Image dockerfile

[See the Dockerfile file](./files/Dockerfile)

```yaml
   # Dockerfile for biimea/aidb:python3.10-drf3.14.0 image build
   # Version: 1.1 - 20221220 

    FROM ubuntu:22.04

    LABEL author=bruno.gas@biimea.com
    LABEL vendor=biimea
    LABEL version=1.1

    # needed for dpkg-reconfigure to be in non interactive mode:
    ARG DEBIAN_FRONTEND=noninteractive

    RUN apt update
    RUN apt full-upgrade -y

    RUN apt install -y git \
        openssh-client \
        vim \
        tzdata \
        libhdf5-dev \
        ffmpeg 

    # For 'default timezone' reconfiguring:
    RUN ln -fs /usr/share/zoneinfo/Europe/Paris /etc/localtime
    RUN dpkg-reconfigure -f noninteractive tzdata

    RUN apt install -y python3 \
        python3-distutils \
        python3-dev \
        python3-venv \
        python3-pip
        
    RUN ln -fs /usr/bin/python3 /usr/bin/python

    RUN python -m pip install --upgrade pip

    RUN pip install django \
        djangorestframework \
        djangorestframework-simplejwt \
        django-cors-headers \
        django-filter \
        dj-rest-auth \
        h5py \
        ffmpeg-python \
        paho-mqtt

    RUN mkdir -p /app
    RUN mkdir /.ssh
    RUN mkdir /data1 && mkdir /data2 && mkdir /data3
    RUN mkdir /base1 && mkdir /base2 && mkdir /base3
    RUN rm -rf /root/.ssh && ln -s /.ssh /root/.ssh

    COPY docker-entrypoint.sh /
    RUN chmod 755 /docker-entrypoint.sh

    WORKDIR /app

    EXPOSE 8000

    ENTRYPOINT ["/docker-entrypoint.sh"]
```

#### Volumes

The container has 8 volumes in its file system named */app, /.ssh, /data1, /data2, /data3, base1, /base2, /base3*.

* ``/app`` is the directory containing the application and its configuration files as well as the *sqlite* database provided it is used;
* ``/.ssh`` is the directory that contains the private and public key to download the application (and update it) from the *Github* repository;
* ``/data1`` to ``/data3`` allow to make mount points with disks containing data sources;
* ``/base1`` to ``/base3`` make it possible to make mount points with disks containing databases made from sources.


!!! Important

    Mounting the */app* directory is not mandatory if the database is outside the container (*dbmysql*, *mariadb*, *postgres*, …), but it is strongly recommanded for internal database (*sqlite*) since this is the only way to preserve data in crash case.

The [docker-entrypoint.sh](files/docker-entrypoint.sh) file get the application source code by cloning the repository. 
It updates it each time the container is restarted:

#### Start script

```bash

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
```

#### Docker-compose 

```yaml
    version: '3.3'

    services:
        aidb:
            image: biimea/aidb:python3.10-drf3.14.0
            container_name: aidb
            restart: unless-stopped
            volumes:
                - aidb_disk2:/data2
                - aidb_disk3:/data3
                - aidb_base1:/base1
                - aidb_base2:/base2
                - ssh-key:/.ssh
                - aidb_app:/app
            ports:
                - 2080:8000
            environment:
                - ALLOWED_HOSTS=dbwelfare.biimea.io
                - DJANGO_SUPERUSER_USERNAME=admin
                - DJANGO_SUPERUSER_PASSWORD=*******
                - DJANGO_SUPERUSER_EMAIL=bruno.gas@beamea.com

    volumes:
        aidb_disk2:
            external: true
        aidb_disk3:
            external: true
        aidb_base1:
            external: true
        aidb_base2:
            external: true
        ssh-key:
            external: true
        aidb_app:
            external: true
```

## Configuring a domain database


*Aidb* lets you build many databases for several applications. 
Each application is defined as a *domain* that can be declared with the following entry:

```bash
    Domain:
        - name
```

A *campaign* is a set of data that have been collected in similar conditions (same place and same date for example):

```bash
    Campaign:
        - domain
        - name
        - date
```

A *Device* is the name and the identifier of the acquisition system used for a given campaign. *Device* entry is:

```bash
    Device:
        - type
        - name
        - identifier
```

The directory the data files are stored in is set using the *Directory* entry:

```bash
    Directory:
        - name
        - absolute path
        - campaign
        - device
```

## Générer un dataset

Un *dataset* désigne une base de donnée de signaux exploitables pour la réalisation d'apprentissages machine. 
*Aidb* n'enregistre pas les datasets sur disque. Ils sont générés à la volée sur requête des utilisateurs.
La génération d'un dataset s'effectue en plusieurs temps:

* Création du dataset (``[POST]/dataset``);
* Téléchargement du dataset (``[GET]/dataset/<id_dataset>/upload``);
* Sauvegarde du dataset (``[PUT]/dataset/<id_dataset>/save``).

La création d'un dataset s'effectue à partir des labels et des contextes définis sur les enregistrements de la base de donnée au moment de la définition.
Le résultat peut donc être différent selon que la labellisation et/ou la contextualisation de la base a changé ou pas entre deux requêtes.
Afin de conserver une structure stable des datasets créés, c'est à dire de pouvoir télécharger un dataset déjà créé sans qu'il soit modifié, les deux opérations de création et de téléchargement sont séparées.
Un dataset est créé une fois, et téléchargé autant de fois que désiré.
Si l'étiquetage de la base de donnée est modifié, le dataset peut être régénéré en en créant un nouveau, puis en le téléchargeant.
En conséquence de tout ceci, un dataset n'est pas modifiable (l'opération ``[PUT]/dataset/<id_dataset>`` n'est pas acceptée).

La requête de création d'un dataset doit comporter tous les paramètres nécéssaires à sa création:

```json
    {
        "name": "dataset name",
        "code": "dataset code",
        "domain": "data domain",
        "labels": [
            "label1", "label2", "label...N"
        ],
        "contexts": [
            "ctx1", "ctx2", "ctx...N"
        ],
        "channels": [0, 1, 2, 3, 4, 5, 6, 7],
        "tags": [
            "tag1", "tag2", "tagN"
        ],
        "comment": "comment",
        "info": {
            "info1", "info...", "infoN"
        }
    }
```

Mais l'enregistrement d'un *dataset* dans la base de donnée comporte des champs supplémentaires cachés:

```json
    {
        "samples": [10, 11, 12],
        "crdate": "date",                 
        "filename": "filename"              
    }
```

* ``samples``: liste des identifiants des segments labelisés au format Json
* ``crdate``: date de création du dataset
* ``filename``: nom du fichier de sauvegarde

La requête de téléchargement ``[GET]/dataset/<id_dataset>/upload`` génère la base de donnée sous la forme d'un fichier ``.h5`` avant sa transmission.
Comme précisé plus haut (requête ``save``), il est possible de réaliser la sauvegarde d'un dataset sur le serveur pour éviter sa regénération à chaque requête de téléchargement.
Une fois la sauvegarde réalisée, le champ ``filename`` de l'enregistrement du dataset est complété.  

Pour détruire cette sauvegarde:

* ``[PUT]/dataset/<id_dataset>/delete``

A ne pas confondre avec la supressionn complete du dataset:

* ``[DELETE]/dataset/<id_dataset>``
