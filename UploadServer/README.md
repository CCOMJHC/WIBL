# WIBL upload-server
This directory contains source code and tools for demonstrating a minimum viable upload server for receiving 
automatic uploads of WIBL data from WIBL loggers and storing the data into AWS S3-compatible object storage.

## AWS deployment
WIBL upload-server can be deployed to AWS using [Terraform](https://developer.hashicorp.com/terraform).

### Prerequisites
These instructions assume you have a POSIX/Linux computing environment (GNU/Linux, macOS, WSL) with the following
installed:

 - [Docker](https://www.docker.com);
 - [AWS cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html); and
 - [Terraform](https://developer.hashicorp.com/terraform/install).

Additionally, if your computer is running Linux on an AMD64 (a.k.a. x86_64) CPU, you'll need to install QEMU 
into your Docker environment to enable building ARM64 binaries (we recommend deploying to ARM64 virtual server 
as they tend to be much cheaper than AMD64). You can do this by running the following command once you've 
installed Docker:
```shell
docker run --privileged --rm tonistiigi/binfmt --install all
```

For more information on enabling multi-platform builds in Docker, see 
[here](https://docs.docker.com/build/building/multi-platform/#qemu).

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
following AWS-managed policies using the [AWS IAM console](https://console.aws.amazon.com/iam/):

- AmazonEC2FullAccess

For more information on how to add IAM identity permissions, see 
[here](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-attach-detach.html).

### Bootstrapping Terraform: Create an S3 bucket for storing and sharing Terraform state
Terraform is able to modify and delete computing resources that were created using Terraform. To do this,
Terraform must store state information about what resources have been created. This state information can be
stored locally on a single compute. However, if the locally stored state information is lost, then you lose
the ability to automatically update or delete the computing resources originally created by Terraform. To
avoid this problem, Terraform state can be [stored remotely in S3](https://developer.hashicorp.com/terraform/language/backend/s3). In addition to providing a disaster
recovery solution, storing state in S3 allows multiple people/computers to manage a WIBL upload-server created 
with Terraform, and to do so asynchronously, without having to worry about each person's updates overwriting
each other.

You can use the script [terraform-bootstrap.bash](scripts/cloud/Terraform/aws/terraform-bootstrap.bash) to 
create an S3 bucket in which to store Terraform state. Before doing so, change the name of the bucket and state
object key by editing `terraform_state_bucket` and `terraform_state_key` in 
[terraform.tfvars](scripts/cloud/Terraform/aws/terraform.tfvars).

Running [terraform-bootstrap.bash](scripts/cloud/Terraform/aws/terraform-bootstrap.bash) will look something like
this:
```shell
$ ./scripts/cloud/Terraform/aws/terraform-bootstrap.bash
CONTENT_ROOT: /Users/JANE_USER/repos/WIBL/UploadServer
Using AWS_TF_ROOT: /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws
Using ARCHITECTURE: arm64
Using AWS_BUILD: aws-build
Using BUILD_DEST: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build
Using CERTS_DEST: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/certs
Using WIBL_UPLOAD_BINARY: upload-server
Using WIBL_UPLOAD_BINARY_PATH: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/upload-server
Using ADD_LOGGER_BINARY: add-logger
Using ADD_LOGGER_BINARY_PATH: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/add-logger
Using WIBL_UPLOAD_CONFIG_PROTO: /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/config-aws.json.proto
Using WIBL_UPLOAD_CONFIG_PATH: /Users/JANE_USER/repos/WIBL/UploadServer/aws-build/config.json
Using AWS_PROFILE: wibl-upload-server
Using TF_VARS: /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/terraform.tfvars
Using WIBL_UPLOAD_SERVER_PORT: 443
Using AWS_REGION: us-east-2
Using TF_STATE_BUCKET: unhjhc-wibl-tf-state
Using TF_STATE_KEY: terraform/state/wibl-upload-server-deploy.tfstate
Using WIBL_UPLOAD_BUCKET_NAME: unhjhc-wibl-upload-server-incoming
Using WIBL_UPLOAD_SNS_TOPIC_NAME: unhjhc-wibl-upload-server-conversion
Using AWS_CLI: aws --profile wibl-upload-server --region us-east-2
Using AWS_ACCOUNT_NUMBER: XXXXXXXXXXXX
Using WIBL_UPLOAD_SNS_TOPIC_ARN: arn:aws:sns:us-east-2:XXXXXXXXXXXX:unhjhc-wibl-upload-server-conversion
Creating terraform state bucket unhjhc-wibl-tf-state in AWS region us-east-2...
{
    "Location": "http://unhjhc-wibl-tf-state.s3.amazonaws.com/"
}
Enabling bucket versioning in terraform state bucket unhjhc-wibl-tf-state...
Done.
```

### Deploying WIBL upload server to AWS using Terraform
Once you have created an S3 bucket for storing and sharing Terraform state, you can then deploy WIBL upload
server to AWS. Before doing this, you *must* edit 
[Terraform variables](scripts/cloud/Terraform/aws/terraform.tfvars). See the "Editing Terraform variables" 
section below for details.

#### Editing Terraform variables
In particular, you *absolutely must* edit the `upload_bucket_name` variable. This is necessary because AWS S3 
bucket names must be unique within an AWS partition; there are currently three partitions: all AWS commercial 
regions, AWS China region, and AWS GovCloud US. Since most users of WIBL upload server will be using an AWS 
commercial region, this means there is effectively a single namespace for S3 bucket names, which means your
bucket name must be unique. A good practice is to include your organization name as well as a random string of
characters in your bucket name, for example "unhjhc-1wdvhu89-wibl-upload". For more information about bucket
naming rules, see [here](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html).

You will probably also want to change the 
[AWS region](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html) to deploy to by 
editing the `aws_region` variable to use your preferred region. When doing so, you must also choose a corresponding 
[availability zone](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-availability-zones.html) 
by editing the `availability_zone` variable.

If you do change the AWS region, you will also need to select a new Amazon Machine Image 
([AMI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html)) by editing the `ami_id` variable. To find
an appropriate AMI ID, you can use the "AMI Catalog" in the AWS EC2 web console to search for an AMI that is 
available in your region and compatible with the CPU architecture of the EC2 instance type you plan to use.  
When choosing an AMI, make sure to choose an "Amazon Linux 2023" AMI for your region and CPU architecture. Once 
you select the AMI, pretend you are going to "Launch Instance with AMI" in the web console where you will be able 
to find the "Image ID" as shown in the red box in the figure below:

![EC2 AMI Image ID example](img/ami.png "AMI Image ID example")

> Note: If you change the `instance_type` variable, you will also have to make sure that your `ami_id` variable 
> is set to a value that is compatible with the CPU architecture of the new instance type. For example, if you 
> switch from the default instance type of `t4g.micro` (which has "AWS Graviton2" CPUs, which uses an "ARM64" 
> architecture) to `t3.micro`, the CPU architecture will be `x86_64`, so you will need to search for an "x86"
> Amazon Linux 2023 AMI. You can use the [Vantage EC2 instance browser](https://instances.vantage.sh) to easily
> browse EC2 instance types. Typically, EC2 instances using AWS Graviton processors will be cheaper than those
> using AMD or Intel processors. If you do change to an `x86_64` instance type, make sure to also change the
> `ARCHITECTURE` variable in [tf-aws-init.sh](scripts/cloud/Terraform/aws/tf-aws-init.sh).

The final [Terraform variable](scripts/cloud/Terraform/aws/terraform.tfvars) you *must* change is `ssh_cidr_block`.
This should be the IP address from which you plan to connect via SSH to your EC2 instance to manage logger
IDs and tokens/passwords. For example, if your public IP address is "128.2.3.4" you would set 
`ssh_cidr_block` to "128.2.3.4/32". You can find the public IPv4 address that your computer is currently using
by using a website such as [Whats My IP](https://whatsmyip.com).

> Note: Using the default value of `ssh_cidr_block="127.0.0.1/32"` will result in your EC2 instance being 
> unreachable via SSH, which will cause the Terraform deployment of the upload-server binary and other
> assets to time out and fail.

#### Terraform deployment
Once you've edited [Terraform variables](scripts/cloud/Terraform/aws/terraform.tfvars) as described above, you can
deploy the WIBL upload server by using the [create.bash script](scripts/cloud/Terraform/aws/create.bash):
```shell
$ ./scripts/cloud/Terraform/aws/create.bash
...
...
...
Apply complete! Resources: 34 added, 0 changed, 0 destroyed.

Outputs:

instance_id = "i-0d996ff6c33dbb700"
instance_private_ip = "10.0.1.77"
instance_public_ip = "42.23.32.24"
internet_gateway_id = "igw-01b0970g42ac855f0"
security_group_id = "sg-0b93e7d5e82759e1e"
ssh_connection_command = "ssh -o 'IdentitiesOnly yes' -i /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/wibl-upload-server-key.pem ec2-user@42.23.32.24"
ssh_key_name = "wibl-upload-server-key"
ssh_private_key_path = "/Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/wibl-upload-server-key.pem"
subnet_cidr = "10.0.1.0/24"
subnet_id = "subnet-01fb0bb7c651868d5"
tls_ca_crt = "/Users/JANE_USER/repos/WIBL/UploadServer/aws-build/certs/ca.crt"
upload_bucket_arn = "arn:aws:s3:::unhjhc-wibl-upload-server-incoming"
upload_topic_arn = "arn:aws:sns:us-east-2:XXXXXXXXXXXX:unhjhc-wibl-upload-server-conversion"
vpc_cidr = "10.0.0.0/16"
vpc_id = "vpc-0e7990ba6c2518eb2"
~/ccom-repos/WIBL/UploadServer
e1d270a9089efca544749da23f5c65a154ebb49972b4b4ae86b36fe1f8b70d18
```

The `create.bash` script creates a lot of output, most of which has been omitted above. At the end you'll see the 
Terraform outputs, in particular the `instance_public_ip` and `ssh_connection_command` variables. You can now use 
the `instance_public_ip` to make an HTTPS request using `curl` (to which you'll have to pass the value of the 
`tls_ca_crt` variable as the `--cacert` option) to test that your WIBL upload server instance is running and 
accessible via the internet:
```shell
$ curl --cacert ./aws-build/certs/ca.crt "https://42.23.32.24" 
checkin
update
```

Now, you should also be able to make an SSH connection to the EC2 instance by copying and pasting the value of the
`ssh_connection_command` (note: Answer "yes" when asked if you want to continue connecting, which you should only
be asked the first time you connect):
```shell
$ ssh -o 'IdentitiesOnly yes' -i /Users/JANE_USER/repos/WIBL/UploadServer/scripts/cloud/Terraform/aws/wibl-upload-server-key.pem ec2-user@42.23.32.24
   ,     #_
   ~\_  ####_        Amazon Linux 2023
  ~~  \_#####\
  ~~     \###|
  ~~       \#/ ___   https://aws.amazon.com/linux/amazon-linux-2023
   ~~       V~' '->
    ~~~         /
      ~~._.   _/
         _/ _/
       _/m/'
Last login: Tue Oct 14 19:25:07 2025 from 128.2.3.4
[ec2-user@ip-10-0-1-51 ~]$ 
```

See the "Managing WIBL upload server" section below for instructions on how to add/delete loggers to/from your
WIBL upload-server instance database, and for general notes on testing and logging/monitoring.

#### Managing WIBL upload-server
Before managing your WIBL upload-server, first make an SSH connection to your EC2 instance as described in the
"Terraform deployment" section above.

##### Add/delete loggers
To add, for example, two loggers to your WIBL upload-server instance database, run the following commands:
```shell
[ec2-user@ip-10-0-1-51 ~]$ cd /usr/local/wibl/upload-server/
sudo -u wibl ./bin/add-logger -config ./etc/config.json -logger TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A -password CC0E1FE1-46CA-4768-93A7-2252BF748118
sudo -u wibl ./bin/add-logger -config ./etc/config.json -logger TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153 -password CAF1CA92-CB9E-437D-B391-7709A39D32B1
```

> Where "TNNAME" is your trusted node identifier.

What the above commands do is run the `add-logger` command as the `wibl` user; the first logger has the identifier
"TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A" with password/token "CC0E1FE1-46CA-4768-93A7-2252BF748118" and the second
logger has the identifier "TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153" with password/token 
"CAF1CA92-CB9E-437D-B391-7709A39D32B1".

Note that if you don't have a password yet for the logger, omit the `-password` option and the code will generate a UUID password for you, then report it on the command line.  Add the `-creds filename` parameter to write this information to a file for transfer locally.  If the installation has updated JSON configuration files that include a path to the CA certificate, this is also reported in the credentials, since this is required for upload configuration on the logger.

To verify that these loggers were added to the database, use the `sqlite3` command line utility:
```shell
[ec2-user@ip-10-0-1-51 ~]$ sqlite3 db/loggers.db 'SELECT * FROM loggers'
TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A|JDJhJDEwJGhyNVVPcWE0MkpTSjVTYjUySnhjZ3VTc1lsQmZqNHZWN2Q3NkNDZ2M5R0dDNWlmM0Vjemh1
TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153|JDJhJDEwJDc1Q0FrVG9WdEo2YUwwWWwxLjN0Ni5vN204NDZZejB6aVB0c0tjQkZEVEtQaXZ5ZlNkSENT
```

> Note: the password is stored in an encrypted field in the database, so you can only see the logger identifier
> in the `sqlite3` output.

To delete the logger with identifier "TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153", use the following `sqlite3` command:
```shell
[ec2-user@ip-10-0-1-51 ~]$ sudo -u wibl sqlite3 db/loggers.db 'DELETE FROM LOGGERS WHERE name="TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153"'
```

To verify that this logger was deleted from the database, use the `sqlite3` command line utility:
```shell
[ec2-user@ip-10-0-1-51 ~]$ sqlite3 db/loggers.db 'SELECT * FROM loggers'
TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A|JDJhJDEwJGhyNVVPcWE0MkpTSjVTYjUySnhjZ3VTc1lsQmZqNHZWN2Q3NkNDZ2M5R0dDNWlmM0Vjemh1
```

##### Test data upload and view logs for requests directly on your EC2 instance
Now that you have a logger in your database, you can post data to the `/checkin` and `/update` server endpoints. For
example, to test the `/checkin` endpoint, first `tail` the WIBL upload-server logs in the terminal window through
which you've connected to the EC2 instance via SSH:
```shell
$ sudo -u wibl tail -f /usr/local/wibl/upload-server/log/*.log
==> /usr/local/wibl/upload-server/log/access.log <==
128.2.3.4 - - [14/Oct/2025:19:21:04 +0000] "GET / HTTP/2.0" 200 0 - curl/8.7.1
34.123.170.104 - - [14/Oct/2025:19:21:35 +0000] "GET / HTTP/2.0" 200 0 - Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/125.0.6422.60 Safari/537.36
205.169.39.21 - - [14/Oct/2025:19:21:37 +0000] "GET / HTTP/2.0" 200 0 https://bing.com/ Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36
205.169.39.21 - - [14/Oct/2025:19:21:43 +0000] "GET / HTTP/2.0" 200 0 - Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36
128.2.3.4 - - [14/Oct/2025:19:21:54 +0000] "GET / HTTP/2.0" 200 0 - curl/8.7.1

==> /usr/local/wibl/upload-server/log/console.log <==
time=2025-10-14T19:19:24.106Z level=INFO msg="starting server on :443"
```

Then, in a separate terminal window, use `curl` to POST dummy data to the `/checkin` endpoint:
```shell
$ curl -v --http1.1 \
        -u TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A:CC0E1FE1-46CA-4768-93A7-2252BF748118 \
        --cacert ./aws-build/certs/ca.crt --fail-with-body "https://42.23.32.24/checkin" \                           
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
*   Trying 42.23.32.24:443...
* Connected to 42.23.32.24 (42.23.32.24) port 443
* ALPN: curl offers http/1.1
* (304) (OUT), TLS handshake, Client hello (1):
*  CAfile: ./aws-build/certs/ca.crt
*  CApath: none
* (304) (IN), TLS handshake, Server hello (2):
* (304) (IN), TLS handshake, Unknown (8):
* (304) (IN), TLS handshake, Certificate (11):
* (304) (IN), TLS handshake, CERT verify (15):
* (304) (IN), TLS handshake, Finished (20):
* (304) (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / AEAD-CHACHA20-POLY1305-SHA256 / [blank] / UNDEF
* ALPN: server accepted http/1.1
* Server certificate:
*  subject: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=Server; CN=ec2-42-23-32-24.us-east-2.compute.amazonaws.com
*  start date: Oct 14 19:18:06 2025 GMT
*  expire date: Oct 12 19:18:06 2035 GMT
*  subjectAltName: host "42.23.32.24" matched cert's IP address!
*  issuer: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=CA; CN=localhost
*  SSL certificate verify ok.
* using HTTP/1.x
* Server auth using Basic with user 'TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A'
> POST /checkin HTTP/1.1
> Host: 42.23.32.24
> Authorization: Basic Rjk0RTg3MUUtOEE2Ni00NjE0LTlFMTAtNjI4RkZDNDk1NDBBOkNDMEUxRkUxLTQ2Q0EtNDc2OC05M0E3LTIyNTJCRjc0ODExOA==
> User-Agent: curl/8.7.1
> Accept: */*
> Content-Type: application/json
> Content-Length: 406
> 
* upload completely sent off: 406 bytes
< HTTP/1.1 200 OK
< Date: Thu, 16 Oct 2025 00:08:41 GMT
< Content-Length: 0
< 
* Connection #0 to host 42.23.32.24 left intact
```

This will result in the log `tail` in the SSH terminal to be updated with the new entry in the access log:
```shell
...
==> /usr/local/wibl/upload-server/log/access.log <==
128.2.3.4 - TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A [14/Oct/2025:19:49:13 +0000] "POST /checkin HTTP/1.1" 200 406 - curl/8.7.1
...
```

If the request was successful, you should '"POST /checkin HTTP/2.0" 200' in the access log entry, the "200" being
the [HTTP status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) for "OK".

Now we can create a test (bogus) WIBL file and upload it using the `/update` endpoint:
```shell
$ WIBL_FILE='dummy.wibl'
dd if=/dev/urandom of="${WIBL_FILE}" bs=8192 count=32
MD5_DIGEST=$(md5sum --quiet $WIBL_FILE)

curl -v --http1.1 \
	-u TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A:CC0E1FE1-46CA-4768-93A7-2252BF748118 \
	--cacert ./aws-build/certs/ca.crt --fail-with-body "https://42.23.32.24/update" \                            

32+0 records in
32+0 records out
262144 bytes transferred in 0.001771 secs (148020327 bytes/sec)
*   Trying 42.23.32.24:443...
* Connected to 42.23.32.24 (42.23.32.24) port 443
* ALPN: curl offers http/1.1
* (304) (OUT), TLS handshake, Client hello (1):
*  CAfile: ./aws-build/certs/ca.crt
*  CApath: none
* (304) (IN), TLS handshake, Server hello (2):
* (304) (IN), TLS handshake, Unknown (8):
* (304) (IN), TLS handshake, Certificate (11):
* (304) (IN), TLS handshake, CERT verify (15):
* (304) (IN), TLS handshake, Finished (20):
* (304) (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / AEAD-CHACHA20-POLY1305-SHA256 / [blank] / UNDEF
* ALPN: server accepted http/1.1
* Server certificate:
*  subject: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=Server; CN=ec2-42-23-32-24.us-east-2.compute.amazonaws.com
*  start date: Oct 14 19:18:06 2025 GMT
*  expire date: Oct 12 19:18:06 2035 GMT
*  subjectAltName: host "42.23.32.24" matched cert's IP address!
*  issuer: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=CA; CN=localhost
*  SSL certificate verify ok.
* using HTTP/1.x
* Server auth using Basic with user 'TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A'
> POST /update HTTP/1.1
> Host: 42.23.32.24
> Authorization: Basic Rjk0RTg3MUUtOEE2Ni00NjE0LTlFMTAtNjI4RkZDNDk1NDBBOkNDMEUxRkUxLTQ2Q0EtNDc2OC05M0E3LTIyNTJCRjc0ODExOA==
> User-Agent: curl/8.7.1
> accept: application/json
> Content-Type: application/octet-stream
> Digest: md5=9e7f557288e8a3c0f09bf05d1ef48901
> Content-Length: 262144
> 
* upload completely sent off: 262144 bytes
< HTTP/1.1 200 OK
< Content-Type: application/json
< Date: Thu, 16 Oct 2025 00:12:43 GMT
< Content-Length: 20
< 
* Connection #0 to host 42.23.32.24 left intact
{"status":"success"}%
```

This will result in the log `tail` in the SSH terminal to be updated with the new entry in the access and console
logs (if you have debug output turned on in [config-aws.json.proto](scripts/cloud/Terraform/aws/config-aws.json.proto)):
```shell
...
==> /usr/local/wibl/upload-server/log/console.log <==
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS: File transfer request with headers:\n"
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS:    Content-Length = [262144]\n"
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS:    Authorization = [Basic Rjk0RTg3MUUtOEE2Ni00NjE0LTlFNDk1NDBBOkNDMEUxRkUxLTQ2Q0EtMTAtNjI4RkZDNDc2OC05M0E3LTIyNTJCRjc0ODExOA==]\n"
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS:    User-Agent = [curl/8.7.1]\n"
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS:    Accept = [application/json]\n"
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS:    Content-Type = [application/octet-stream]\n"
time=2025-10-14T19:59:47.049Z level=DEBUG msg="TRANS:    Digest = [md5=ccae97189b9f203426a66077b15ccef2]\n"
time=2025-10-14T19:59:47.068Z level=DEBUG msg="TRANS: File from logger with 262144 bytes in body.\n"
time=2025-10-14T19:59:47.068Z level=INFO msg="TRANS: successful recomputation of MD5 hash for transmitted contents.\n"
time=2025-10-14T19:59:47.070Z level=DEBUG msg="AWS-S3: checking for bucket unhjhc-wibl-upload-server-incoming.\n"
time=2025-10-14T19:59:47.225Z level=INFO msg="Bucket unhjhc-wibl-upload-server-incoming exists and you already own it."
time=2025-10-14T19:59:47.225Z level=DEBUG msg="AWS-S3: transferring 55c48228-a938-11f0-8a1e-02160b114f4f.wibl to bucket unhjhc-wibl-upload-server-incoming (262144 bytes).\n"
time=2025-10-14T19:59:47.281Z level=DEBUG msg="AWS-SNS: publishing key 55c48228-a938-11f0-8a1e-02160b114f4f.wibl on topic arn:aws:sns:us-east-2:XXXXXXXXXXXX:unhjhc-wibl-upload-server-conversion.\n"
time=2025-10-14T19:59:47.332Z level=DEBUG msg="TRANS: sending |{\"status\":\"success\"}| to logger as response.\n"

==> /usr/local/wibl/upload-server/log/access.log <==
128.2.3.4 - TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A [14/Oct/2025:19:59:47 +0000] "POST /update HTTP/1.1" 200 262144 - curl/8.7.1

...
```

##### Log rotation and viewing logs in AWS CloudWatch
Because WIBL upload-server is meant to be a reliable, long-running service, log file archiving and deletion, also
known as log rotation, are provided for. Without log rotation, a long-running service runs the risk of filling up 
its disk with log files, meaning that the service would eventually become unavailable.

The default logging configuration for WIBL upload-server can be found in the "logging" section in the prototype
configuration file found [here](scripts/cloud/Terraform/aws/config-aws.json.proto).

> Note: this file is used by [create.bash](scripts/cloud/Terraform/aws/create.bash) to create the configuration 
> file that is uploaded to your EC2 instance as part of the Terraform deployment).

The "logging" section of the default configuration is reproduced below:
```
"logging": {
    "level": "debug",
    "console_log": "/usr/local/wibl/upload-server/log/console.log",
    "access_log": "/usr/local/wibl/upload-server/log/access.log",
    "max_size_mb": 1,
    "max_age": 1,
    "max_backups": 0,
    "compress_rotated": false
}
```

There are two log files, the access log and console log. Access log logs all HTTPS requests, whether they 
are successful or not. The access log is useful for verifying that loggers are successfully uploading data to WIBL
upload-server. It's also useful to detecting potential attempts by nefarious actors to access the server. 
The console log shows more detailed messages about errors that may occur as well as debugging information. The
`level` configuration key controls the level of detail in the console log, with "error" only logging error 
conditions, while "warning" logs messages warning of potential problems (in addition to those messages logged
at the "error" level). The "info" level logs informational messages that might aid in debugging (in addition
to logging "warning" and "error" level messages), with "debug" providing the most detailed logging (in addition
to all "info", "warning", and "error" level messages).

In terms of log rotation, the relevant keys of the logging configration are `max_size_mb`, `max_age`, `max_backups`,
and `compress_rotated`. With the default configuration, WIBL upload-server will rotate the console and access logs
once the log files reach one-MiB in size (i.e., `"max_size_mb": 1`). Archived log files are named according to the 
pattern "name-timestamp.ext", so "/usr/local/wibl/upload-server/log/access.log" would be archived to 
"/usr/local/wibl/upload-server/log/access-2025-10-15T13-49-13.234.log" upon rotation. Archived log files are retained
until they are one-day-old (i.e., `"max_age": 1`). All archived files younger than one-day-old will be retained
(i.e., `"max_backups": 0,`), and archived log files will NOT be compressed (i.e., `"compress_rotated": false`). These
configuration choices were chosen in harmony with the CloudWatch configuration described below. For more information
on log file retention and rotation, see the [lumberjack documentation](https://github.com/natefinch/lumberjack?tab=readme-ov-file#cleaning-up-old-log-files).

###### AWS CloudWatch configuration and viewing
To access the most up-to-date logging data, SSH into your EC2 instance and tail the console or access logs as
described above. However, for longer term archiving and visualization of logs, WIBL upload-server is configured
to automatically send logs to [AWS CloudWatch](https://docs.aws.amazon.com/cloudwatch/) using the 
[CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Agent-on-EC2-Instance.html). 
You can access your CloudWatch logs via the [AWS console](https://aws.amazon.com).

You can view and modify the Cloudwatch agent configuration used by WIBL upload-server by editing the 
[userdata.sh](scripts/cloud/Terraform/aws/userdata.sh) script, which is used by the Terraform deployment to do 
final configuration of the EC2 instance used by WIBL upload-server. The relevant section of `userdata.sh` is
reproduced below:
```shell
...
# Setup CloudWatch agent
cat > /tmp/cloudwatch-agent.json <<-HERE
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "log_group_name": "wibl-upload-server",
            "log_stream_name": "amazon-cloudwatch-agent.log",
            "timezone": "UTC",
            "auto_removal": false,
            "retention_in_days": 60
          },
          {
            "file_path": "/usr/local/wibl/upload-server/log/console-*.log",
            "log_group_name": "wibl-upload-server",
            "log_stream_name": "console.log",
            "timezone": "UTC",
            "auto_removal": false,
            "retention_in_days": 60
          },
          {
            "file_path": "/usr/local/wibl/upload-server/log/access-*.log",
            "log_group_name": "wibl-upload-server",
            "log_stream_name": "access.log",
            "timezone": "UTC",
            "auto_removal": false,
            "retention_in_days": 60
          }
        ]
      }
    }
  }
}
HERE
sudo mv /tmp/cloudwatch-agent.json /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json
...
```

The CloudWatch agent will copy access and console logs to CloudWatch once they have been rotated and archived. 
This can be seen by the `"file_path"` pattern specified for each 
(e.g., `"/usr/local/wibl/upload-server/log/access-*.log"`). Until log rotation, you can only view logs by SSHing to
the EC2 instance as described above. Log data will be retained in CloudWatch for 60-days (i.e., `"retention_in_days": 60`).
CloudWatch agent will NOT delete log files once they have been copied to CloudWatch (i.e., `"auto_removal": false`);
log deletion is handled by WIBL upload-server (as described above).

To access your WIBL upload-server CloudWatch logs using the AWS Console, go to the CloudWatch service, click on
on "Logs > Log groups" and search for "upload-server" as shown in the figure below:

![CloudWatch log group search](img/cloudwatch-log-group.png "CloudWatch log group search")

After clicking on the "wibl-upload-server" log group, you should see one or more log streams as shown here:

![WIBL upload-server log streams](img/cloudwatch-log-streams.png "WIBL upload-server log streams")

At first, you will only see the "amazon-cloudwatch-agent.log" log stream. This log stream is just the log for the
CloudWatch agent itself, which is running on your EC2 instance and is responsible for copying rotated
access and console logs to CloudWatch; this is useful for monitoring whether and when copying of these log
entries to CloudWatch occurs. Once either console.log or access.log have been rotated and archived
at least once, log entries for these log files will appear in the "console.log" or "access.log" log streams. The
figure below shows an excerpt of log entries for "access.log" (the IP address of each log entry has been redacted):

![WIBL upload-server access log stream](img/cloudwatch-access-log.png "WIBL upload-server access log stream")


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
./add-logger -config config-local.json -logger TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A -password CC0E1FE1-46CA-4768-93A7-2252BF748118
./add-logger -config config-local.json -logger TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153 -password CAF1CA92-CB9E-437D-B391-7709A39D32B1
```

> Where "TNNAME" is your trusted node identifier.

You can then verify that the loggers have been added by running:
```shell
$ sqlite3 ./db/loggers.db 'SELECT * FROM loggers'
TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A|JDJhJDEwJGhyNVVPcWE0MkpTSjVTYjUySnhjZ3VTc1lsQmZqNHZWN2Q3NkNDZ2M5R0dDNWlmM0Vjemh1
TNNAME-12CEC8B4-0C42-424C-82CD-FB4E96CD7153|JDJhJDEwJDc1Q0FrVG9WdEo2YUwwWWwxLjN0Ni5vN204NDZZejB6aVB0c0tjQkZEVEtQaXZ5ZlNkSENT
```

Next, you can do a basic test of the upload-server by using the `/checkin` endpoint using `curl`:
```shell
$ curl -v --http1.1 \
        -u TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A:CC0E1FE1-46CA-4768-93A7-2252BF748118 \
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
* ALPN: curl offers http/1.1
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
* ALPN: server accepted http/1.1
* Server certificate:
*  subject: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=Server; CN=localhost
*  start date: Oct  9 19:07:05 2025 GMT
*  expire date: Oct  9 19:07:05 2026 GMT
*  subjectAltName: host "localhost" matched cert's "localhost"
*  issuer: C=US; ST=NewHampshire; L=Durham; O=CCOM-JHC; OU=CA; CN=localhost
*  SSL certificate verify ok.
* using HTTP/1.x
* Server auth using Basic with user 'TNNAME-F94E871E-8A66-4614-9E10-628FFC49540A'
> POST /checkin HTTP/1.1
> Host: localhost:8000
> Authorization: Basic Rjk0RTg3MUUtOEE2Ni00NjE0LTlFMTAtNjI4RkZDNDk1NDBBOkNDMEUxRkUxLTQ2Q0EtNDc2OC05M0E3LTIyNTJCRjc0ODExOA==
> User-Agent: curl/8.7.1
> Accept: */*
> Content-Type: application/json
> Content-Length: 406
> 
* upload completely sent off: 406 bytes
< HTTP/1.1 200 OK
< Date: Thu, 16 Oct 2025 00:03:39 GMT
< Content-Length: 0
< 
* Connection #0 to host localhost left intact
```

You can see from the above output that the request was successful because
the HTTP status code was 200, i.e., `HTTP/2 200`.

In the console in which you are running `docker compose up`, you should
also see the following output:
```shell
wibl-upload  | 2025/10/02 18:13:35.002803 INFO 172.19.0.1 - TNNAME-35A7C0C1-3EFD-42EE-AE61-69EEF8455E1F [02/Oct/2025:18:13:35 +0000] "POST /checkin HTTP/1.1" 200 406
```

If the logger was not known (i.e., not in the loggers.db file), you would
instead see output like:
```shell
wibl-upload  | 2025/10/02 16:38:41.325695 INFO DB: Logger TNNAME-35A7C0C1-3EFD-42EE-AE61-69EEF8455E1F not found in database.
```

Finally, you can test uploading a dummy file to the upload-server by using the `/update` endpoint using `curl`:
```shell
WIBL_FILE='dummy.wibl'
dd if=/dev/urandom of="${WIBL_FILE}" bs=8192 count=32
MD5_DIGEST=$(md5sum --quiet $WIBL_FILE)

curl -v --http1.1 \
	-u TNNAME-35A7C0C1-3EFD-42EE-AE61-69EEF8455E1F:9A066573-7F4F-4FE7-B5DD-0D1F672B40BA \
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
