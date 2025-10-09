#!/bin/bash -v

dnf install -y golang

mkdir -p /usr/local/wibl/upload-server/bin \
    /usr/local/wibl/upload-server/etc/certs \
    /usr/local/wibl/upload-server/db \
    /usr/local/wibl/upload-server/log
