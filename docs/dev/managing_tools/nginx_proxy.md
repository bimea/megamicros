# Nginx as proxy server

## Starting with nginx container

Here is an example of docker-compose.yml file entry for *Nginx*:

```bash
    ...
    nginx:
        image: nginx
        container_name: nginx
        restart: unless-stopped
        volumes:
          - /data1/containers/nginx/conf.d:/etc/nginx/conf.d
          - /data1/containers/nginx/certificate:/etc/nginx/certificate
          - /data1/containers/certbot/www/:/var/www/certbot/:ro
          - /data1/containers/certbot/conf/:/etc/nginx/ssl/:ro
        ports:
          - 80:80
          - 443:443
```

The ``conf.f`` directory should be already installed with configuration files inside before starting th container. If not, the ``conf.d`` inside the container would be empty.
If you have no configuration file model, comment the mounting line, start the container then save the generated configuration files. Stop the container and after having copied the files in the mount directory, retstart the container.

```bash
    $ > docker-compose up nginx
    [CTRL C]
    $ > docker-compose start
```

## Reverse proxy with ssl support

```bash
    > apt install certbot
    > cerbot --version
```

See [HTTPS using Nginx and Let's encrypt in Docker](https://mindsers.blog/post/https-using-nginx-certbot-docker/)

```bash
    > docker compose run --rm certbot certonly --webroot --webroot-path /var/www/certbot/ --dry-run -d your_domain.fr 
    Creating sdi-proxy_certbot_run ... done
    Saving debug log to /var/log/letsencrypt/letsencrypt.log
    Simulating a certificate request for sdi.ppi.ingenierie.upmc.fr
    The dry run was successful.

    > docker compose run --rm  certbot certonly --webroot --webroot-path /var/www/certbot/ -d your_domain.fr
    Account registered.
    Requesting a certificate for sdi.ppi.ingenierie.upmc.fr

    Successfully received certificate.
    Certificate is saved at: /etc/letsencrypt/live/sdi.ppi.ingenierie.upmc.fr/fullchain.pem
    Key is saved at:         /etc/letsencrypt/live/sdi.ppi.ingenierie.upmc.fr/privkey.pem
    This certificate expires on 2023-11-04.
    These files will be updated when the certificate renews.

    NEXT STEPS:
    - The certificate will need to be renewed before it expires. Certbot can automatically renew the certificate in the background, but you may need to take steps to enable that functionality. See https://certbot.org/renewal-setup for instructions.

    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    If you like Certbot, please consider supporting our work by:
     * Donating to ISRG / Let's Encrypt:   https://letsencrypt.org/donate
     * Donating to EFF:                    https://eff.org/donate-le
    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
```

On Let's encrypt certificat can serve multiple sub domains. For example:

```bash
    > docker compose run --rm  certbot certonly --webroot --webroot-path /var/www/certbot/ -d your_domain.fr, sub1.yourdomain.fr, sub2.yourdomain.fr 
```

## Renewing

```bash
    > docker compose run --rm certbot renew
```