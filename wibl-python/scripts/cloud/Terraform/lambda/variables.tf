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

variable "aws_region" {
    type = string
}

variable "lambda_timeout" {
    type = number
    default = 10
}

variable "architecture" {
    type = string
    default = "arm64"
}

# TODO This layer name will change depending on the deployed region, as well as the version
variable "numpy_layer_name" {
    type = string
    default = "arn:aws:lambda:us-west-1:336392948345:layer:AWSSDKPandas-Python311-Arm64:23"
}

variable "python_version" {
    type = string
    default = "3.12"
}

variable "lambda_memory_size" {
    type = number
    default = 128
}

variable "staging_bucket_arn" {
    type = string
}

variable "incoming_bucket_arn" {
    type = string
}

variable "incoming_bucket_id" {
    type = string
}

variable "viz_bucket_arn" {
    type = string
}

variable TOPIC_ARN_VALIDATION {
    type = string
    default = ""
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

variable private_subnet {
    type = string
    default = ""
}

variable private_sg {
    type = string
    default = ""
}

variable "conversion_topic_arn" {
    type = string
    default = ""
}

variable "validation_topic_arn" {
    type = string
    default = ""
}

variable "submission_topic_arn" {
    type = string
    default = ""
}

variable "submitted_topic_arn" {
    type = string
    default = ""
}

variable "provider_auth" {
    type = string
    default = ""
}

variable "account_number" {
    type = string
    default = "111111111110"
}

variable "package_path" {
    type = string
}

