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

variable "static_bucket_name" {
    description = "Name of the static bucket"
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
    sensitive = true
}

variable "manager_db_size" {
    type = string
}

variable "manager_db_name" {
    type = string
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