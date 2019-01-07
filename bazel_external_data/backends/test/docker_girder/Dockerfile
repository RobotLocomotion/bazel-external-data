# Adapted from girder/girder.
# Builds a Girder instance ready for testing with `external_data`.
FROM node:6

EXPOSE 8080

RUN apt-get update && \
  apt-get install -qy software-properties-common && \
  apt-get update && apt-get install -qy \
    build-essential \
    git \
    libffi-dev \
    libsasl2-dev \
    libldap2-dev \
    libpython-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py

WORKDIR /
RUN git clone https://github.com/girder/girder && \
  cd girder && \
  git checkout 95cfbec

WORKDIR /girder
RUN pip install -I six>=1.11  # Dumb...
RUN pip install -e .[plugins]
RUN girder-install web --all-plugins

ARG db

ENV GIRDER_MONGO_URI=$db

# N.B. We cannot run `setup_database.py` because it requires mongo, which is in
# another container. Defer running this to `setup_server.py`.
# @see https://github.com/docker/compose/issues/3227
# This can be mitigated by merging the MongoDB Dockerfile into here... blech.
COPY ./files /tmp/files
COPY ./setup_server.yml /tmp/setup_server.yml

ENTRYPOINT ["python", "-m", "girder"]
