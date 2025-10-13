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
  domain   = "vpc"
}

module "wibl_tls" {
  depends_on = [aws_eip.wibl_upload_ip]
  source = "./modules/wibl_tls"

  out_dir = var.wibl_certs_path
  server_common_name = aws_eip.wibl_upload_ip.public_dns
  server_cert_dns_names = [aws_eip.wibl_upload_ip.public_dns]
  server_cert_ip_addrs =  [aws_eip.wibl_upload_ip.public_ip]
}

resource "aws_eip_association" "eip_assoc" {
  instance_id   = aws_instance.ec2_instance.id
  allocation_id = aws_eip.wibl_upload_ip.id
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
  from_port         = var.wibl_upload_server_port
  ip_protocol       = "tcp"
  to_port           = var.wibl_upload_server_port
}

# IAM roles to allow EC2 instance access to S3 bucket and SNS topic
data "aws_iam_policy_document" "upload_bucket_policy_doc" {
  statement {
    sid = "EC2AllowS3AccessUpload"

    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.upload_bucket.arn,
      "${aws_s3_bucket.upload_bucket.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "upload_bucket_policy" {
  name        = var.upload_bucket_name
  description = "Allow"
  policy = data.aws_iam_policy_document.upload_bucket_policy_doc.json
}

data "aws_iam_policy_document" "upload_sns_policy_doc" {
  statement {
    sid = "EC2AllowSNSAccessUpload"

    effect = "Allow"
    actions = [
      "SNS:Publish"
    ]
    resources = [
      aws_sns_topic.upload_topic.arn
    ]
  }
}

resource "aws_iam_policy" "upload_sns_policy" {
  name        = var.upload_sns_topic_name
  description = "Allow"
  policy = data.aws_iam_policy_document.upload_sns_policy_doc.json
}

data "aws_iam_policy_document" "ec2_instance_role_policy_doc" {
  statement {
    sid = "EC2AllowS3AccessUpload"

    effect = "Allow"
    actions = [
      "sts:AssumeRole"
    ]
    principals {
      identifiers = ["ec2.amazonaws.com"]
      type = "Service"
    }
  }
}

resource "aws_iam_role" "ec2_instance" {
  name = "wibl_upload_ec2_instance_role"
  assume_role_policy = data.aws_iam_policy_document.ec2_instance_role_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "upload_bucket_policy" {
  role       = aws_iam_role.ec2_instance.name
  policy_arn = aws_iam_policy.upload_bucket_policy.arn
}

resource "aws_iam_role_policy_attachment" "upload_sns_policy" {
  role       = aws_iam_role.ec2_instance.name
  policy_arn = aws_iam_policy.upload_sns_policy.arn
}

resource "aws_iam_role_policy_attachment" "cloud_watch_policy" {
  role       = aws_iam_role.ec2_instance.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "wibl_upload" {
  name = "wibl_upload_profile"
  role = aws_iam_role.ec2_instance.name
}

# EC2 instance
resource "aws_instance" "ec2_instance" {
  depends_on = [aws_eip.wibl_upload_ip, module.wibl_tls]

  ami                    = var.ami_id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.wibl_upload.id
  key_name               = aws_key_pair.ec2_key_pair.key_name
  vpc_security_group_ids = [aws_security_group.wibl_upload_server.id]
  subnet_id              = aws_subnet.public.id

  # Use user data to install necessary software packages and
  # setup the server directories
  user_data = file("${path.module}/userdata.sh")

  # Note: For file provisioning we use the temporary public IP of the instance since trying
  # to use the Elastic IP here won't work because it hasn't been associated yet.
  provisioner "file" {
    source      = var.wibl_upload_binary_path
    destination = "/tmp/upload-server"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = var.add_logger_binary_path
    destination = "/tmp/add-logger"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = var.wibl_upload_config_path
    destination = "/tmp/config.json"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = "${module.wibl_tls.certificate_directory}/server.crt"
    destination = "/tmp/server.crt"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = "${module.wibl_tls.certificate_directory}/server.key"
    destination = "/tmp/server.key"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = "${module.wibl_tls.certificate_directory}/ca.crt"
    destination = "/tmp/ca.crt"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "remote-exec" {
    inline = [
      "sudo mkdir -p /usr/local/wibl/upload-server/bin /usr/local/wibl/upload-server/etc/certs",
      "sudo mv /tmp/upload-server /usr/local/wibl/upload-server/bin",
      "sudo mv /tmp/add-logger /usr/local/wibl/upload-server/bin",
      "sudo mv /tmp/config.json /usr/local/wibl/upload-server/etc",
      "sudo mv /tmp/*.crt /tmp/server.key /usr/local/wibl/upload-server/etc/certs"
    ]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

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
