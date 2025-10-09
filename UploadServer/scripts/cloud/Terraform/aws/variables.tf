variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "wibl_upload_binary_path" {
  description = "Path to upload server compiled binary to be provisioned to the EC2 image"
  type        = string
  default     = "aws-build/upload-server"
}

variable "wibl_upload_config_path" {
  description = "Path to upload server config file to be provisioned to the EC2 image"
  type        = string
  default     = "aws-build/config.json"
}

variable "wibl_upload_server_crt_path" {
  description = "Path to upload server server.crt file to be provisioned to the EC2 image"
  type        = string
  default     = "aws-build/certs/server.crt"
}

variable "wibl_upload_server_key_path" {
  description = "Path to upload server server.key file to be provisioned to the EC2 image"
  type        = string
  default     = "aws-build/certs/server.key"
}

variable "wibl_upload_ca_crt_path" {
  description = "Path to upload server ca.crt file to be provisioned to the EC2 image"
  type        = string
  default     = "aws-build/certs/ca.crt"
}

variable "upload_bucket_name" {
  description = "Name of the S3 bucket to write uploads to"
  type = string
}

variable "upload_sns_topic_name" {
  description = "Name of the SNS topic to notify on upload"
  type = string
}

variable "availability_zone" {
  description = "Availability zone for the subnet"
  type        = string
  default     = "us-east-2a"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "key_name" {
  description = "Name for the SSH key pair"
  type        = string
  default     = "wibl-upload-server-key"
}

variable "instance_name" {
  description = "Name tag for the EC2 instance and related resources"
  type        = string
  default     = "wibl-upload-server"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.micro"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance"
  type        = string
}

variable "wibl_upload_server_port" {
  description = "TCP port that upload-server should listen on"
  type        = number
  default     = 443
}

variable "ssh_cidr_block" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"  # Warning: Allows SSH from anywhere. Restrict in production!
}

variable "https_cidr_block" {
  description = "CIDR block allowed to HTTPS into the instance"
  type        = string
  default     = "0.0.0.0/0"  # Note: Allows HTTPS from anywhere.
}

variable "root_volume_size" {
  description = "Size of root volume in GB"
  type        = number
  default     = 20
}
