FROM ubuntu:latest AS runner
WORKDIR /srv
RUN apt-get update && apt-get install -y build-essential && apt-get clean autoclean && apt-get autoremove --yes
RUN groupadd nobody && \
    useradd -c "NetRun user" -g nobody -m netrun


COPY ./netrun /srv/netrun
RUN cd netrun/serve/s4g_chroot && \
    make install && \
    cd ../sandrun_export && \
		make && \
		cp sandserv /home/netrun &&\
    cp *.sh /home/netrun/ &&\
    cd /home/netrun && \
		./perm.sh

CMD ["/home/netrun/sandserv.sh"]
