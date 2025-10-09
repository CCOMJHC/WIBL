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

resource "aws_eip" "wibl_upload_ip" {
  instance = aws_instance.ec2_instance.id
  domain   = "vpc"
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

# Generate SSH key pair
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create AWS key pair using the generated public key
resource "aws_key_pair" "ec2_key_pair" {
  key_name   = var.key_name
  public_key = tls_private_key.ec2_key.public_key_openssh
}

# Save private key locally
resource "local_file" "private_key" {
  content         = tls_private_key.ec2_key.private_key_pem
  filename        = "${path.cwd}/${var.key_name}.pem"
  file_permission = "0400"
}

# Security group for SSH access
resource "aws_security_group" "wibl_upload_server" {
  name        = "${var.instance_name}-sg"
  description = "Security group allowing SSH and HTTPS access"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${var.instance_name}-sg"
  }
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.wibl_upload_server.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}

resource "aws_vpc_security_group_ingress_rule" "allow_ssh_ipv4" {
  security_group_id = aws_security_group.wibl_upload_server.id
  cidr_ipv4         = var.ssh_cidr_block
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

resource "aws_vpc_security_group_ingress_rule" "allow_tls_ipv4" {
  security_group_id = aws_security_group.wibl_upload_server.id
  cidr_ipv4         = var.https_cidr_block
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443
}

# EC2 instance
resource "aws_instance" "ec2_instance" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.ec2_key_pair.key_name
  vpc_security_group_ids = [aws_security_group.wibl_upload_server.id]
  subnet_id              = aws_subnet.public.id
  # We're using an EIP, so don't bother creating an ephemeral public IP
  associate_public_ip_address = false

  # Use user data to install necessary software packages and
  # setup the server directories
  user_data = file("${path.module}/userdata.sh")

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name = var.instance_name
  }

  lifecycle {
    create_before_destroy = true
  }
}
