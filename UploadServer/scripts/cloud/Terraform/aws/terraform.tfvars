aws_region="us-east-2"
availability_zone="us-east-2a"
vpc_cidr="10.0.0.0/16"
subnet_cidr="10.0.1.0/24"
key_name="wibl-upload-server-key"
instance_name="wibl-upload-server"
instance_type="t4g.micro"
ami_id="ami-0f22ddbe09d4dba64"  # Valid Amazon Linux 2023 ARM64 AMI for us-east-2

wibl_upload_server_port=443
ssh_cidr_block="127.0.0.1/32"  # Restrict to your IP
https_cidr_block="0.0.0.0/0" # Restrict if you need to, otherwise, use default

upload_bucket_name="unhjhc-wibl-upload-server-incoming"
upload_sns_topic_name="unhjhc-wibl-upload-server-conversion"
