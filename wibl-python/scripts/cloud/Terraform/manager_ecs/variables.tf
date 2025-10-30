variable "region" {
    description = "aws region"
    type = string
}

variable "incoming_bucket_name" {
    description = "Name of the incoming s3 bucket"
    type = string
}

variable "staging_bucket_name" {
    description = "Name of the staging s3 bucket"
    type = string
}

variable "viz_bucket_name" {
    description = "Name of the viz s3 bucket"
    type = string
}

variable "viz_lambda_name" {
    type = string
}

variable "architecture" {
    type = string
    default = "arm64"
}

variable "src_path" {
    type = string
}

variable "account_number" {
    type = string
}