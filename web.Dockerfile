FROM ubuntu:latest
WORKDIR /srv
RUN apt-get update && apt-get install -y build-essential && apt-get clean autoclean && apt-get autoremove --yes

COPY ./netrun /srv/netrun
RUN cd netrun/serve/sandrun_export && make

FROM ubuntu/apache2:latest
WORKDIR /srv

# Install perl cgi and openssl
RUN apt-get update && apt-get install -y libcgi-pm-perl openssl && apt-get clean autoclean && apt-get autoremove --yes

# Generate self-signed SSL certificates
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/apache-selfsigned.key \
  -out /etc/ssl/certs/apache-selfsigned.crt \
  -subj "/C=US/ST=Alaska/L=Fairbanks/O=Netrun/OU=Netrun/CN=localhost"

# Enable apache ssl certs
RUN a2enmod ssl cgi

COPY ./resources/apache.conf /etc/apache2/sites-available/000-default.conf
COPY ./www /srv/www
COPY ./netrun /srv/netrun

COPY --from=0 /srv/netrun/serve/sandrun_export/sandsend netrun/bin/sandsend
# Create needed directory scaffolding
RUN mkdir netrun/pwreset
RUN touch netrun/.htpasswd

# Update permissions
RUN chown -R www-data:www-data /srv
