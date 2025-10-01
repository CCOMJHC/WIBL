FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

RUN dnf install -y golang

WORKDIR /var/local/wibl/upload-server

COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./
COPY src/ ./src/

RUN CGO_ENABLED=0 GOOS=linux go build -o /var/local/wibl/upload-server/upload-server

COPY config.json ./

ENTRYPOINT ["/var/local/wibl/upload-server/upload-server", "-config", "config.json", "-level", "debug"]
