terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.93"
    }
  }

  backend "s3" {
    bucket = var.terraform_state_bucket
    region = var.region
    key    = var.terraform_state_key
  }
}

locals {
  region = var.region
}

provider "aws" {
  region = local.region
}

module "buckets" {
  source = "./buckets"

  upload_bucket = var.upload_bucket_name
}

module "sns" {
  source = "./sns"

  upload_topic = var.upload_sns_topic_name
}

module "vpc" {
  source = "./vpc"

  vpc_cidr = var.vpc_cidr
}

module "subnets" {
  source     = "./subnets"
  vpc_id     = module.vpc.vpc_id
  cidr_block = var.public_subnet_cidr
}

module "ec2" {
  source = "./ec2"

  upload_server_ami = var.upload_server_ami
}