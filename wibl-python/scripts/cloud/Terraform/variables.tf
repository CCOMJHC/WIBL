variable "region" {
    description = "aws region"
    type = string
}

variable "src_path" {
    type = string
    description = "Path to the wibl-python directory"
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

variable "static_bucket_name" {
    description = "Name of the bucket that holds the frontend's static files"
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
    sensitive = true
}

variable "manager_db_name" {
    type = string
}

variable "manager_db_size" {
    type = string
    description = "The size of the managers database in GB"
}

variable "manager_db_user" {
    type = string
}

variable "manager_db_password" {
    type = string
    sensitive = true
}

variable "frontend_db_name" {
    type = string
}

variable "frontend_db_size" {
    type = string
    description = "The size of the frontend database in GB"
}

variable "frontend_db_user" {
    type = string
}

variable "frontend_db_password" {
    type = string
    sensitive = true
}

variable "superuser_username" {
    type = string
}

variable "superuser_password" {
    type = string
    sensitive = true
}

variable "frontend_secret_key" {
    type = string
    sensitive = true
}

variable "debug_mode" {
    type = string
}

variable "domain_host_name" {
    type = string
}
