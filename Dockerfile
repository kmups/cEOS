ARG CEOSBASE=${CEOSBASE}
ARG CEOSBASE_TAG=${CEOSBASE_TAG}
FROM ${CEOSBASE}:${CEOSBASE_TAG}
ENV INTFTYPE=eth
ENV ETBA=1
ENV SKIP_ZEROTOUCH_BARRIER_IN_SYSDBINIT=1
ENV CEOS=1
ENV EOS_PLATFORM=ceoslab
ENV MGMT_INTF=eth0
ENV container=docker
EXPOSE 21/tcp
EXPOSE 22/tcp
EXPOSE 80/tcp
EXPOSE 8080/tcp
EXPOSE 443/tcp
EXPOSE 4443/tcp
EXPOSE 830/tcp
EXPOSE 6030/tcp
EXPOSE 161/udp
COPY Pci.py /usr/lib/python2.7/site-packages/Pci.py
VOLUME [ "/mnt/flash" ]
CMD /sbin/init systemd.setenv=INTFTYPE=eth systemd.setenv=ETBA=1 systemd.setenv=SKIP_ZEROTOUCH_BARRIER_IN_SYSDBINIT=1 systemd.setenv=CEOS=1 systemd.setenv=EOS_PLATFORM=ceoslab systemd.setenv=MGMT_INTF=eth0 systemd.setenv=container=docker
