data "aws_caller_identity" "current" {}

# Generate SSH key pair
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_eip" "wibl_upload_ip" {
  domain   = "vpc"
}

# Create AWS key pair using the generated public key
resource "aws_key_pair" "ec2_key_pair" {
  key_name   = var.key_name
  public_key = tls_private_key.ec2_key.public_key_openssh
}

# Save private key locally
resource "local_file" "private_key" {
  content         = tls_private_key.ec2_key.private_key_pem
  filename        = "${var.ec2_private_key_dir}/${var.key_name}.pem"
  file_permission = "0400"
}

# Security group for SSH access
resource "aws_security_group" "wibl_upload_server" {
  name        = "${var.instance_name}-sg"
  description = "Security group allowing SSH and HTTPS access"
  vpc_id      = var.vpc_id

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
      var.upload_bucket_arn,
      "${var.upload_bucket_arn}/*"
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
      var.upload_sns_topic_arn
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
  depends_on = [aws_eip.wibl_upload_ip]

  ami                    = var.ami_id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.wibl_upload.id
  key_name               = aws_key_pair.ec2_key_pair.key_name
  vpc_security_group_ids = [aws_security_group.wibl_upload_server.id]
  subnet_id              = var.public_subnet_id

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
    source      = "${var.wibl_tls_certificate_directory}/server.crt"
    destination = "/tmp/server.crt"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = "${var.wibl_tls_certificate_directory}/server.key"
    destination = "/tmp/server.key"

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = tls_private_key.ec2_key.private_key_pem
      host        = self.public_ip
    }
  }

  provisioner "file" {
    source      = "${var.wibl_tls_certificate_directory}/ca.crt"
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

resource "aws_eip_association" "eip_assoc" {
  instance_id   = aws_instance.ec2_instance.id
  allocation_id = var.public_ip_id
}