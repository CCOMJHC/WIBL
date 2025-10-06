variable "region" {
    description = "aws region"
    type = string
}

variable "terraform_state_bucket" {
    description = "Name of the S3 bucket to store Terraform state in"
    type = string
}

variable "terraform_state_key" {
    description = "Key of the S3 object to store Terraform state in"
    type = string
}

variable "upload_bucket_name" {
    description = "Name of the S3 bucket to write uploads to"
    type = string
}

variable "upload_sns_topic_name" {
    description = "Name of the SNS topic to notify on upload"
    type = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "upload_server_ami" {
  description = "AMI to use for WIBL upload-server EC2 instance"
  type        = string
}
