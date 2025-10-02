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
RUN go mod download

COPY *.go ./
COPY src/ ./src/

RUN CGO_ENABLED=1 GOOS=linux go build -o /usr/local/wibl/upload-server/bin/upload-server

ENTRYPOINT ["/usr/local/wibl/upload-server/bin/upload-server", "-config", "/usr/local/wibl/upload-server/etc/config.json"]
