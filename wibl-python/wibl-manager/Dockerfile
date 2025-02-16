FROM --platform=linux/arm64 python:3.11-slim AS builder

WORKDIR /usr/src/wibl
ADD ./ /usr/src/wibl

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install curl so that our healthcheck works under Docker
RUN apt-get update -y
RUN apt-get install -y curl

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install '.[server]'

FROM builder as final

EXPOSE 5000

CMD ["wibl-manager"]
