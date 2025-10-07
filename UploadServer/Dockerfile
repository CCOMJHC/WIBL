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
COPY build-upload-server.bash ./

RUN UPLOAD_SERVER_OUT=/usr/local/wibl/upload-server/bin/upload-server ./build-upload-server.bash

ENTRYPOINT ["/usr/local/wibl/upload-server/bin/upload-server", "-config", "/usr/local/wibl/upload-server/etc/config.json"]
