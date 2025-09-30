terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  alias  = "aws"
  region = "us-east-1"
}

resource "aws_lambda_layer_version_permission" "allow_localstack" {
  layer_name      = "AWSSDKPandas-Python311-Arm64"
  version_number  = 23
  principal       = "localstack-testing"
  statement_id    = "AllowLocalstackAccess"
  action          = "lambda:GetLayerVersion"
}

module "configure-buckets" {
    source = "./buckets"

    incoming_bucket = var.incoming_bucket_name
    staging_bucket = var.staging_bucket_name
    viz_bucket = var.viz_bucket_name
}

module "configure-sns" {
    source = "./sns"

    conversion_topic_name = var.conversion_topic_name
    validation_topic_name = var.validation_topic_name
    submission_topic_name = var.submission_topic_name
    submitted_topic_name = var.submitted_topic_name
}

module "configure-subnets_efs" {
    count = var.use_localstack ? 0 : 1
    source = "./subnets_efs"
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

    conversion_lambda_role_name = var.conversion_lambda_role_name
    conversion_start_lambda_role_name = var.conversion_start_lambda_role_name
    validation_lambda_role_name = var.validation_lambda_role_name
    submission_lambda_role_name = var.submission_lambda_role_name
    viz_lambda_role_name = var.viz_lambda_role_name

    staging_bucket_arn = module.configure-buckets.staging_bucket_arn
    incoming_bucket_arn = module.configure-buckets.incoming_bucket_arn
    incoming_bucket_id = module.configure-buckets.incoming_bucket_id
    viz_bucket_arn = module.configure-buckets.viz_bucket_arn

    private_subnet = var.use_localstack ? "" : module.configure-subnets_efs.private_subnet
    private_sg = var.use_localstack ? "" : module.configure-subnets_efs.private_sg

    conversion_topic_arn = module.configure-sns.conversion_topic_arn
    validation_topic_arn = module.configure-sns.validation_topic_arn
    submission_topic_arn = module.configure-sns.submission_topic_arn
    submitted_topic_arn = module.configure-sns.submitted_topic_arn
    depends_on = [module.configure-buckets, module.configure-sns, module.configure-subnets_efs]
}