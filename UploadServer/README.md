# WIBL upload-server
This directory contains source code and tools for demonstrating
a minimum viable upload server for receiving automatic uploads
from WIBL data from WIBL loggers and storing the data into AWS 
S3-compatible object storage.

## AWS deployment
WIBL upload-server can be deploy to AWS using [Terraform](https://developer.hashicorp.com/terraform).

### Prerequisites
These instructions assume you have a POSIX/Linux computing environment (GNU/Linux, macOS, WSL) with the following
installed:

 - [Docker](https://www.docker.com);
 - [AWS cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html); and
 - [Terraform](https://developer.hashicorp.com/terraform/install).

### Create AWS CLI profile for WIBL upload-server
To avoid accidentally creating many cloud resources in the wrong AWS account when testing
and using WIBL upload-server you must create an AWS CLI profile specific to WIBL upload-server:
```shell
$ aws configure --profile wibl-upload-server
```

You will then be prompted to enter your `AWS Access Key ID`, `AWS Secret Access Key`,
`Default region name` and the `Default output format`. The key ID and key can be
generated for your user by using the AWS IAM console. For region name, enter `us-east-1`
(unless you have a reason to use another region). For output format, enter `json` (some
WIBL upload-server setup scripts rely on being able to parse JSON output from AWS CLI commands).

Before being able to use to create and manage a WIBL upload-server instance, it is necessary to 
add certain IAM roles to the AWS account you want to use. To do so, first make sure to add the 
following AWS-managed policies using the IAM console:

- AmazonEC2FullAccess

[To add the remaining required policies to your AWS account, run:
```shell
# TODO: Implement if needed
#./scripts/cloud/Terraform/aws/add-user-roles.bash
```
]

### Bootstrapping Terraform: Create bucket for storing and sharing Terraform state
Terraform state can be [stored remotely in S3](https://developer.hashicorp.com/terraform/language/backend/s3). 
This allows multiple people/computers to manage a WIBL upload-server created with Terraform asynchronously.

You can use the script [terraform-bootstrap.bash](scripts/cloud/Terraform/aws/terraform-bootstrap.bash) to 
create an S3 bucket in which to store Terraform state. Before doing so, change the name of the bucket and state
object key by editing `terraform_state_bucket` and `terraform_state_key` in 
[terraform.tfvars](scripts/cloud/Terraform/aws/terraform.tfvars).

## Local development and testing
WIBL upload-server can be developed and tested locally using
`docker compose`.

### Prerequisites
These instructions assume you have a POSIX/Linux computing environment (GNU/Linux, macOS, WSL) with the following 
installed: 

 - [Go](https://go.dev/dl/);
 - [SQLite](https://www.sqlite.org/index.html);
 - [curl](https://curl.se);
 - [Docker](https://www.docker.com); and
 - [OpenSSL](https://openssl-library.org).

Make sure to download and install the correct version of Go by 
reading the required version from [go.mod](go.mod), for example:
```shell
$ grep -e '^go' go.mod 
go 1.24
```

### Building and running with `docker compose`
Before running, you'll need to first create a self-signed TLS
certificate using the provided script [cert-gen.sh](scripts/cert-gen.sh).

This should store the certs in the local directory called `certs`
(which will be created if it does not exist).

Now, build and start the server in a container using:
```shell
$ docker compose up
[+] Building 24.7s (16/16) FINISHED                                             
 => [internal] load local bake definitions                                 0.0s
 => => reading from stdin 563B                                             0.0s
 => [internal] load build definition from Dockerfile                       0.0s
 => => transferring dockerfile: 698B                                       0.0s
 => [internal] load metadata for public.ecr.aws/amazonlinux/amazonlinux:2  0.5s
 => [internal] load .dockerignore                                          0.0s
 => => transferring context: 2B                                            0.0s
 => [1/9] FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal@sha256  0.0s
 => => resolve public.ecr.aws/amazonlinux/amazonlinux:2023-minimal@sha256  0.0s
 => [internal] load build context                                          0.0s
 => => transferring context: 11.63kB                                       0.0s
 => CACHED [2/9] RUN dnf install -y golang                                 0.0s
 => CACHED [3/9] RUN mkdir -p /usr/local/wibl/upload-server     /usr/loca  0.0s
 => CACHED [4/9] WORKDIR /usr/local/wibl/upload-server                     0.0s
 => CACHED [5/9] COPY go.mod go.sum ./                                     0.0s
 => CACHED [6/9] RUN go mod download                                       0.0s
 => [7/9] COPY *.go ./                                                     0.0s
 => [8/9] COPY src/ ./src/                                                 0.0s
 => [9/9] RUN CGO_ENABLED=1 GOOS=linux go build -o /usr/local/wibl/uploa  20.4s
 => exporting to image                                                     3.4s
 => => exporting layers                                                    2.9s
 => => exporting manifest sha256:81c59b0c98f655c1e57904e50f3c02e849ea1aad  0.0s
 => => exporting config sha256:5b6e0480545f55c4ca0efcb3ef1515b291994a68f5  0.0s
 => => exporting attestation manifest sha256:780ce69e210d12089489d32047fb  0.0s
 => => exporting manifest list sha256:66efb0eea48a2cce9a501ac96f3584eb896  0.0s
 => => naming to docker.io/library/wibl-upload-wibl-upload:latest          0.0s
 => => unpacking to docker.io/library/wibl-upload-wibl-upload:latest       0.4s
 => resolving provenance for metadata file                                 0.0s
[+] Running 2/2
 ✔ wibl-upload-wibl-upload  Built                                          0.0s 
 ✔ Container wibl-upload    Recreated                                      0.3s 
Attaching to wibl-upload
wibl-upload  | 2025/10/02 15:46:12.322007 starting server on :8000
wibl-upload  | 2025/10/02 18:10:52.451089 INFO [::1] - - [02/Oct/2025:18:10:52 +0000] "GET / HTTP/2.0" 200 0
wibl-upload  | 2025/10/02 18:11:02.497117 INFO [::1] - - [02/Oct/2025:18:11:02 +0000] "GET / HTTP/2.0" 200 0
wibl-upload  | 2025/10/02 18:11:12.556534 INFO [::1] - - [02/Oct/2025:18:11:12 +0000] "GET / HTTP/2.0" 200 0
```

Before trying to interact with the service, you'll need to create a `loggers.db`
file in the `db` local directory. Before you can do that, you'll need to build
the `add-logger` command using the provided [script](build-add-logger.bash).


```shell
mkdir -p db
./add-logger -config config-local.json -logger F94E871E-8A66-4614-9E10-628FFC49540A -password CC0E1FE1-46CA-4768-93A7-2252BF748118
./add-logger -config config-local.json -logger 12CEC8B4-0C42-424C-82CD-FB4E96CD7153 -password CAF1CA92-CB9E-437D-B391-7709A39D32B1
```

You can then verify that the loggers have been added by running:
```shell
$ sqlite3 ./db/loggers.db 'SELECT * FROM loggers'
name          hash            
------------  ----------------
F94E871E-8A6  JDJhJDEwJG90M3RK
6-4614-9E10-  dlJRbS9ZM3JOd2Zq
628FFC49540A  UUYxQXVsUHd4Nk94
              NHNSNEJJb2VjQWo4
              YVlkU1laOUlURHM2

12CEC8B4-0C4  JDJhJDEwJDJNOHpE
2-424C-82CD-  Z1laMzd4MnRlU3FC
FB4E96CD7153  cXdPaS5sYWNzQWw1
              RFV3a3BuZzlTM09T
              QjFFdVhYdS9FY3h
```

Next, you can do a basic test of the upload-server by using the `/checkin` endpoint using `curl`:
```shell
$ curl -v \
        -u F94E871E-8A66-4614-9E10-628FFC49540A:CC0E1FE1-46CA-4768-93A7-2252BF748118 \
        --cacert ./certs/ca.crt --fail-with-body "https://localhost:8000/checkin" \
  -H 'Content-Type: application/json' \
  --data @-<<EOF
{
 "version": {
   "firmware": "1.5.5",
   "commandproc": "1.4.0",
   "nmea0183": "1.0.1",
   "nmea2000": "1.1.0",
   "imu": "1.0.0",
   "serialiser": "1.3"
 },
 "elapsed": 12345678,
 "webserver": {
   "current": "dummy status",
   "boot": "dummy boot"
 },
 "data": {
   "nmea0183": {
     "count": 0,
     "detail": []
   },
   "nmea2000": {
     "count": 0,
     "detail": []
   }
 },
 "files": {
   "count": 0,
   "detail": []
 }
}
EOF
* Host localhost:8000 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
*   Trying [::1]:8000...
* Connected to localhost (::1) port 8000
* ALPN: curl offers h2,http/1.1
* (304) (OUT), TLS handshake, Client hello (1):
*  CAfile: ./certs/ca.crt
*  CApath: none
* (304) (IN), TLS handshake, Server hello (2):
* (304) (IN), TLS handshake, Unknown (8):
* (304) (IN), TLS handshake, Certificate (11):
* (304) (IN), TLS handshake, CERT verify (15):
* (304) (IN), TLS handshake, Finished (20):
* (304) (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / AEAD-CHACHA20-POLY1305-SHA256 / [blank] / UNDEF
* ALPN: server accepted h2
* Server certificate:
*  subject: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=Server; CN=localhost
*  start date: Oct  1 18:08:25 2025 GMT
*  expire date: Oct  1 18:08:25 2026 GMT
*  subjectAltName: host "localhost" matched cert's "localhost"
*  issuer: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=CA; CN=localhost
*  SSL certificate verify ok.
* using HTTP/2
* Server auth using Basic with user 'F94E871E-8A66-4614-9E10-628FFC49540A'
* [HTTP/2] [1] OPENED stream for https://localhost:8000/checkin
* [HTTP/2] [1] [:method: POST]
* [HTTP/2] [1] [:scheme: https]
* [HTTP/2] [1] [:authority: localhost:8000]
* [HTTP/2] [1] [:path: /checkin]
* [HTTP/2] [1] [authorization: Basic Rjk0RTg3MUUtOEE2Ni00NjE0LTlFMTAtNjI4RkZDNDk1NDBBOkNDMEUxRkUxLTQ2Q0EtNDc2OC05M0E3LTIyNTJCRjc0ODExOA==]
* [HTTP/2] [1] [user-agent: curl/8.7.1]
* [HTTP/2] [1] [accept: */*]
* [HTTP/2] [1] [content-type: application/json]
* [HTTP/2] [1] [content-length: 406]
> POST /checkin HTTP/2
> Host: localhost:8000
> Authorization: Basic Rjk0RTg3MUUtOEE2Ni00NjE0LTlFMTAtNjI4RkZDNDk1NDBBOkNDMEUxRkUxLTQ2Q0EtNDc2OC05M0E3LTIyNTJCRjc0ODExOA==
> User-Agent: curl/8.7.1
> Accept: */*
> Content-Type: application/json
> Content-Length: 406
> 
* upload completely sent off: 406 bytes
< HTTP/2 200 
< content-length: 0
< date: Thu, 02 Oct 2025 16:36:44 GMT
< 
* Connection #0 to host localhost left intact
```

You can see from the above output that the request was successful because
the HTTP status code was 200, i.e., `HTTP/2 200`.

In the console in which you are running `docker compose up`, you should
also see the following output:
```shell
wibl-upload  | 2025/10/02 18:13:35.002803 INFO 172.19.0.1 - 35A7C0C1-3EFD-42EE-AE61-69EEF8455E1F [02/Oct/2025:18:13:35 +0000] "POST /checkin HTTP/2.0" 200 406
```

If the logger was not known (i.e., not in the loggers.db file), you would
instead see output like:
```shell
wibl-upload  | 2025/10/02 16:38:41.325695 INFO DB: Logger 35A7C0C1-3EFD-42EE-AE61-69EEF8455E1F not found in database.
```

Finally, you can test uploading a dummy file to the upload-server by using the `/update` endpoint using `curl`:
```shell
WIBL_FILE='dummy.wibl'
dd if=/dev/urandom of="${WIBL_FILE}" bs=8192 count=32
MD5_DIGEST=$(md5sum --quiet $WIBL_FILE)

curl -v \
	-u 35A7C0C1-3EFD-42EE-AE61-69EEF8455E1F:9A066573-7F4F-4FE7-B5DD-0D1F672B40BA \
	--cacert ./certs/ca.crt --fail-with-body "https://localhost:8000/update" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/octet-stream' \
        -H "Digest: md5=$MD5_DIGEST" \
        --data-binary "@${WIBL_FILE}"
```

If successful, the server will return a JSON document that looks like this:
```JSON
{"status":"success"}
```

If there was a failure, the server will return:
```JSON
{"status":"failure"}
```

And the server console log should show the error so that you can fix it.

To view the contents of the localstack S3 bucket to verify that the uploaded file was written to storage, you can
use the `aws cli` as follows:
```shell
export UPLOAD_BUCKET='unhjhc-wibl-incoming'
export AWS_REGION=us-east-2
export AWS_ENDPOINT=http://127.0.0.1:14566
export AWS_ACCESS_KEY_ID='test'
export AWS_SECRET_ACCESS_KEY='test'

aws --endpoint-url $AWS_ENDPOINT --region $AWS_REGION s3api list-objects --bucket $UPLOAD_BUCKET 
{
    "Contents": [
        {
            "Key": "ebfe2337-a095-11f0-8e53-f6c927ddf09b.wibl",
            "LastModified": "2025-10-03T20:17:01+00:00",
            "ETag": "\"35b61c938f8c08d926ffd167729748d5\"",
            "ChecksumAlgorithm": [
                "CRC64NVME"
            ],
            "ChecksumType": "FULL_OBJECT",
            "Size": 262144,
            "StorageClass": "STANDARD",
            "Owner": {
                "DisplayName": "webfile",
                "ID": "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a"
            }
        }
    ],
    "RequestCharged": null,
    "Prefix": ""
}
```
