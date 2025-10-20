FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

RUN dnf install -y golang

RUN mkdir -p /usr/local/wibl/upload-server \
    /usr/local/wibl/upload-server/bin \
    /usr/local/wibl/upload-server/etc \
    /usr/local/wibl/upload-server/etc/certs \
    /usr/local/wibl/upload-server/db \
    /usr/local/wibl/upload-server/log
WORKDIR /usr/local/wibl/upload-server

COPY go.mod go.sum ./
COPY *.go ./
COPY src/ ./src/
COPY build-add-logger.bash ./
COPY build-upload-server.bash ./

WORKDIR /usr/local/wibl/upload-server/src/tools/add-logger
RUN ADD_LOGGER_OUT=/usr/local/wibl/upload-server/bin/add-logger ../../../build-add-logger.bash

WORKDIR /usr/local/wibl/upload-server
RUN UPLOAD_SERVER_OUT=/usr/local/wibl/upload-server/bin/upload-server ./build-upload-server.bash

ENTRYPOINT ["/usr/local/wibl/upload-server/bin/upload-server", "-config", "/usr/local/wibl/upload-server/etc/config.json"]
