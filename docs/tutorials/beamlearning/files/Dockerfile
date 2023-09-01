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
        ffmpeg-python

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