terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket = "unhjhc-wibl-tf-state"
    region = "us-east-2"
    key    = "terraform/state/wibl-upload-server-deploy.tfstate"
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "upload_bucket" {
  bucket = var.upload_bucket_name
  force_destroy = true
}

resource "aws_sns_topic" "upload_topic" {
  name = var.upload_sns_topic_name
}

# Create VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.instance_name}-vpc"
  }
}

# Create Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.instance_name}-igw"
  }
}

# Create public subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.instance_name}-public-subnet"
  }
}

# Create route table for public subnet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.instance_name}-public-rt"
  }
}

# Associate route table with public subnet
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

module "public_ip" {
  source = "./modules/public_ip"
}

module "wibl_tls" {
  depends_on = [module.public_ip]
  source = "./modules/wibl_tls"

  out_dir = var.wibl_certs_path
  server_common_name = module.public_ip.public_dns
  server_cert_dns_names = [module.public_ip.public_dns]
  server_cert_ip_addrs =  [module.public_ip.public_ip]
}

module "upload_server" {
  depends_on = [module.public_ip, module.wibl_tls]
  source = "./modules/upload_server"

  ami_id                         = var.ami_id
  ec2_private_key_dir            = path.cwd
  public_ip_id                   = module.public_ip.id
  public_subnet_id               = aws_subnet.public.id
  upload_bucket_arn              = aws_s3_bucket.upload_bucket.arn
  upload_bucket_name             = aws_s3_bucket.upload_bucket.bucket
  upload_sns_topic_name          = aws_sns_topic.upload_topic.name
  upload_sns_topic_arn           = aws_sns_topic.upload_topic.arn
  vpc_id                         = aws_vpc.main.id
  wibl_tls_certificate_directory = module.wibl_tls.certificate_directory
}
