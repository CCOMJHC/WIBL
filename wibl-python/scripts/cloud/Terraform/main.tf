terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }

  required_version = ">= 1.5.0"
}

provider "docker" {
  alias = "ecr"
  registry_auth {
    address  = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com"
    username = data.aws_ecr_authorization_token.ecr.user_name
    password = data.aws_ecr_authorization_token.ecr.password
  }
}

data "aws_ecr_authorization_token" "ecr" {}

provider "aws" {
  region = var.region
  s3_use_path_style = true
}

module "configure-buckets" {
    source = "./buckets"

    incoming_bucket = var.incoming_bucket_name
    staging_bucket = var.staging_bucket_name
    viz_bucket = var.viz_bucket_name
    static_bucket = var.static_bucket_name
}

module "configure-sns" {
    source = "./sns"

    conversion_topic_name = var.conversion_topic_name
    validation_topic_name = var.validation_topic_name
    submission_topic_name = var.submission_topic_name
    submitted_topic_name = var.submitted_topic_name
}

module "configure-manager-ecs" {
    source = "./manager_ecs"

    region = var.region
    account_number = var.account_number
    incoming_bucket_name = var.incoming_bucket_name
    staging_bucket_name = var.staging_bucket_name
    viz_bucket_name = var.viz_bucket_name
    viz_lambda_name = var.viz_lambda_name
    static_bucket_name = var.static_bucket_name

    architecture = var.architecture
    src_path = var.src_path
    manager_db_size = var.manager_db_size
    manager_db_name = var.manager_db_name
    manager_db_user = var.manager_db_user
    manager_db_password = var.manager_db_password
    frontend_db_name = var.frontend_db_name
    frontend_db_size = var.frontend_db_size
    frontend_db_user = var.frontend_db_user
    frontend_db_password = var.frontend_db_password

    superuser_username = var.superuser_username
    superuser_password = var.superuser_password

    frontend_secret_key = var.frontend_secret_key
    origin_secret = var.origin_secret
    debug_mode = var.debug_mode
    providers = {
        docker = docker.ecr
        aws = aws
    }
}

module "configure-lambda" {
    source = "./lambda"

    aws_region = var.region
    package_path = "${var.wibl_build_path}/wibl-package-py${var.python_version}-${var.architecture}.zip"
    conversion_lambda_name = var.conversion_lambda_name
    conversion_start_lambda_name = var.conversion_start_lambda_name
    validation_lambda_name = var.validation_lambda_name
    submission_lambda_name = var.submission_lambda_name
    viz_lambda_name = var.viz_lambda_name

    account_number = var.account_number
    MANAGEMENT_URL = module.configure-manager-ecs.manager_url

    conversion_lambda_role_name = var.conversion_lambda_role_name
    conversion_start_lambda_role_name = var.conversion_start_lambda_role_name
    validation_lambda_role_name = var.validation_lambda_role_name
    submission_lambda_role_name = var.submission_lambda_role_name
    viz_lambda_role_name = var.viz_lambda_role_name

    staging_bucket_arn = module.configure-buckets.staging_bucket_arn
    staging_bucket_name = var.staging_bucket_name
    incoming_bucket_arn = module.configure-buckets.incoming_bucket_arn
    incoming_bucket_name = var.incoming_bucket_name
    incoming_bucket_id = module.configure-buckets.incoming_bucket_id
    viz_bucket_arn = module.configure-buckets.viz_bucket_arn

    private_subnet = module.configure-manager-ecs.private_subnet
    private_sg = module.configure-manager-ecs.private_sg

    conversion_topic_arn = module.configure-sns.conversion_topic_arn
    validation_topic_arn = module.configure-sns.validation_topic_arn
    submission_topic_arn = module.configure-sns.submission_topic_arn
    submitted_topic_arn = module.configure-sns.submitted_topic_arn
    depends_on = [module.configure-buckets, module.configure-sns, module.configure-manager-ecs]
}