#!/bin/bash
# This generates a set of certificates for self-signing, which can be used for testing the logger on the
# local network.  These should not, obviously, be used in production over the open internet!  The IP address
# of the test server connected to the logger's WiFi is almost always 192.168.4.2 (the logger is always
# 192.168.4.1 when booted as an AP), which is assumed in the CA and server setup below.  You may have to adjust
# for your particular test environment.  You should obviously also change the SUBJECT_* variable descriptions.
#
# Typically, you'd want to make the certificates in ./certs (the Go code also assumes that it'll find them
# there).  Note that you need to upload ca.cert to the logger to allow for TLS to work, but the upload
# mechanism assumes something that will be *.txt; you can simply copy ca.cert to ca-cert.txt for this.
#
# The source for this came from a GitHub issue report (https://github.com/espressif/arduino-esp32/issues/6060),
# so attribution is unknown (apart from the username, which leads to https://github.com/potatcode).  We'd like
# to thank the contributor for providing the clues on how to generate the certificates required for this
# correctly.
#
# As a consequence of the unknown status of this script, this file has no license information.  We'd assume that
# it's effectively public domain, or at least open source, but have no evidence to that effect.

export PATH=/opt/homebrew/opt/openssl/bin:${PATH}

CA_IP_CN="localhost"
SERVER_IP_CN="localhost"
CLIENT_HOSTNAME="wibl-logger"

SUBJECT_CA="/C=US/ST=NewHampshire/L=Durham/O=CCOM-JHC/OU=CA/CN=$CA_IP_CN"
SUBJECT_SERVER="/C=US/ST=NewHampshire/L=Durham/O=CCOM-JHC/OU=Server/CN=$SERVER_IP_CN"
SUBJECT_CLIENT="/C=US/ST=NewHampshire/L=Durham/O=CCOM-JHC/OU=Client/CN=$CLIENT_HOSTNAME"

SAN="subjectAltName=DNS:localhost,IP:127.0.0.1"

function generate_CA () {
   echo "$SUBJECT_CA"
   openssl req -x509 -nodes -sha256 -newkey rsa:2048 -subj "$SUBJECT_CA"  -days 365 \
      -addext $SAN \
      -keyout ca.key -out ca.crt
}

function generate_server () {
   echo "$SUBJECT_SERVER"
   openssl req -nodes -sha256 -new -subj "$SUBJECT_SERVER" \
      -addext $SAN \
      -keyout server.key -out server.csr
   openssl x509 -req -copy_extensions copy -sha256 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365
}

function generate_client () {
   echo "$SUBJECT_CLIENT"
   openssl req -new -nodes -sha256 -subj "$SUBJECT_CLIENT" \
      -addext $SAN \
      -out client.csr -keyout client.key 
   openssl x509 -req -sha256 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365
}

generate_CA
generate_server
generate_client