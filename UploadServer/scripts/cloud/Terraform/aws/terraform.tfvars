terraform_state_bucket="unhjhc-wibl-tf-state"
terraform_state_key="terraform/state/wibl-upload-server-deploy.tfstate"

aws_region="us-east-2"
#aws_region="ca-central-1"
availability_zone="us-east-2a"
#availability_zone="ca-central-1a"

upload_bucket_name="unhjhc-wibl-upload-server-incoming"
upload_sns_topic_name="unhjhc-wibl-upload-server-conversion"

instance_type="t4g.micro"  # ARM64-based AWS Graviton2 processor: 2 vCPUs, 1 GiB memory
ami_id="ami-0f22ddbe09d4dba64"  # Amazon Linux 2023 ARM64 AMI for us-east-2
# ami_id="ami-0a8d9645d76629a78"  # Amazon Linux 2023 ARM64 AMI for ca-central-1

vpc_cidr="10.0.0.0/16"
subnet_cidr="10.0.1.0/24"
key_name="wibl-upload-server-key"
instance_name="wibl-upload-server"

wibl_upload_server_port=443
ssh_cidr_block="127.0.0.1/32"  # Restrict to your IP
https_cidr_block="0.0.0.0/0" # Restrict if you need to, otherwise, use default
