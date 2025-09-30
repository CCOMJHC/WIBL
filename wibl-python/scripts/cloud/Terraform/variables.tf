variable "use_localstack" {
    type = bool
    default = false
}

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

variable "conversion_lambda_name" {
    type = string
}

variable "conversion_start_lambda_name" {
    type = string
}

variable "validation_lambda_name" {
    type = string
}

variable "submission_lambda_name" {
    type = string
}

variable "viz_lambda_name" {
    type = string
}

variable "conversion_lambda_role_name" {
    type = string
}

variable "conversion_start_lambda_role_name" {
    type = string
}

variable "validation_lambda_role_name" {
    type = string
}

variable "submission_lambda_role_name" {
    type = string
}

variable "viz_lambda_role_name" {
    type = string
}


variable DCDB_PROVIDER_ID {
    type = string
    default = ""
}

variable DCDB_UPLOAD_URL {
    type = string
    default = ""
}

variable MANAGEMENT_URL {
    type = string
    default = ""
}

variable "conversion_topic_name" {
    type = string
    default = ""
}

variable "validation_topic_name" {
    type = string
    default = ""
}

variable "submission_topic_name" {
    type = string
    default = ""
}

variable "submitted_topic_name" {
    type = string
    default = ""
}

variable "wibl_build_path" {
    type = string
}

variable "architecture" {
    type = string
    default = "arm64"
}

variable "python_version" {
    type = string
    default = "3.12"
}

variable "account_number" {
    type = string
}