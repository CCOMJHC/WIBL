FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

RUN dnf install -y golang

RUN mkdir -p /var/local/wibl/upload-server \
    /var/local/wibl/upload-server/bin \
    /var/local/wibl/upload-server/etc \
    /var/local/wibl/upload-server/etc/certs \
    /var/local/wibl/upload-server/db \
    /var/local/wibl/upload-server/log
WORKDIR /var/local/wibl/upload-server

COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./
COPY src/ ./src/

RUN CGO_ENABLED=1 GOOS=linux go build -o /var/local/wibl/upload-server/bin/upload-server

ENTRYPOINT ["/var/local/wibl/upload-server/bin/upload-server", "-config", "/var/local/wibl/upload-server/etc/config.json"]
