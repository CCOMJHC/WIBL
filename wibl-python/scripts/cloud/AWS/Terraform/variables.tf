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
    description = "Name of the conversion lambda"
    type = string
}

variable "conversion_start_lambda_name" {
    description = "Name of the conversion start lambda"
    type = string
}

variable "validation_lambda_name" {
    description = "Name of the validation lambda"
    type = string
}

variable "submission_lambda_name" {
    description = "Name of the submission lambda"
    type = string
}

variable "viz_lambda_name" {
    description = "Name of the visualization lambda"
    type = string
}

variable "conversion_lambda_role_name" {
    description = "Name of the AWS IAM role attached to the conversion lambda"
    type = string
}

variable "conversion_start_lambda_role_name" {
    description = "Name of the AWS IAM role attached to the conversion start lambda"
    type = string
}

variable "validation_lambda_role_name" {
    description = "Name of the AWS IAM role attached to the validation lambda"
    type = string
}

variable "submission_lambda_role_name" {
    description = "Name of the AWS IAM role attached to the submission lambda"
    type = string
}

variable "viz_lambda_role_name" {
    description = "Name of the AWS IAM role attached to the visualization lambda"
    type = string
}

variable DCDB_provider_id {
    description = "The pre-provided ID used to upload the DCDB"
    type = string
}

variable DCDB_test_url {
    description = "The URL used to upload to the test DCDB server"
    type = string
}

variable DCDB_prod_url {
    description = "The URL used to upload to the production DCDB server"
    type = string
    sensitive = true
}

variable DCDB_mode {
    description = "If the value is 1, the production url will be used for DCDB upload, if it is 0 the test URL will be used."
    type = string
}

variable "conversion_topic_name" {
    description = "The name of the AWS SNS topic used to trigger the conversion lambda"
    type = string
}

variable "validation_topic_name" {
    description = "The name of the AWS SNS topic used to trigger the validation lambda"
    type = string
}

variable "submission_topic_name" {
    description = "The name of the AWS SNS topic used to trigger the submission lambda"
    type = string
}

variable "submitted_topic_name" {
    description = "The name of the AWS SNS used to notify of file submission"
    type = string
}

variable "wibl_build_path" {
    description = "The build path containing the compiled wibl executable"
    type = string
}

variable "architecture" {
    description = "The architecture being run by the ECS tasks"
    type = string
    default = "arm64"
}

variable "python_version" {
    type = string
    default = "3.12"
}

variable "account_number" {
    description = "User's default AWS account number"
    type = string
    sensitive = true
}

variable "manager_db_name" {
    description = "Manager's database name"
    type = string
}

variable "manager_db_size" {
    description = "The size of the managers database in GB"
    type = string
}

variable "manager_db_user" {
    description = "The Postgres username for the manager database"
    type = string
}

variable "manager_db_password" {
    description = "The Postgres password for the manager database"
    type = string
    sensitive = true
}

variable "frontend_db_name" {
    description = "Frontend's database name"
    type = string
}

variable "frontend_db_size" {
    description = "The size of the frontend database in GB"
    type = string
}

variable "frontend_db_user" {
    description = "The Postgres username for the frontend database"
    type = string
}

variable "frontend_db_password" {
    description = "The Postgres password for the frontend database"
    type = string
    sensitive = true
}

variable "superuser_username" {
    description = "The Django superuser's username for the frontend"
    type = string
}

variable "superuser_password" {
    description = "The Django superuser's password for the frontend"
    type = string
    sensitive = true
}

variable "frontend_secret_key" {
    description = "The Django secret key used to encrypt the frontend"
    type = string
    sensitive = true
}

variable "debug_mode" {
    type = string
}

variable "origin_secret" {
    description = "A unique value used to encrypt traffic between the CloudFront and the frontend's load balancer"
    type = string
    sensitive = true
}

variable "map_name" {
    type = string
}

variable "auth_file_name" {
    description = "The name of the file located in the 'auth' folder that contains your DCDB provider auth string"
    type = string
}
