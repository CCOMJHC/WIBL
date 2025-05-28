resource "aws_vpc" "main_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
}

resource "aws_subnet" "public_subnet_1" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.2.0/24"
    availability_zone = "us-east-1b"
    tags = {
      Name = "wibl-public"
    }
}

resource "aws_subnet" "public_subnet_2" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.4.0/24"
    availability_zone = "us-east-1a"
    tags = {
      Name = "wibl-public2"
    }
}

resource "aws_eip" "elastic_ip" {
    domain = "vpc"
}

resource "aws_nat_gateway" "nat_gateway" {
    allocation_id = aws_eip.elastic_ip.id
    subnet_id = aws_subnet.public_subnet_1.id

    tags = {
      Name = "wibl-lambda-net"
    }
}

resource "aws_internet_gateway" "ig_public" {
  vpc_id = aws_vpc.main_vpc.id

  tags = {
    Name = "wibl-public"
  }
}

resource "aws_route_table" "public_route_table" {
    vpc_id = aws_vpc.main_vpc.id

    tags = {
        Name = "wibl-public"
    }

    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.ig_public.id
    }
}

resource "aws_route_table_association" "public1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "public2" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_security_group" "pubic_sg" {
    name = "wibl-mgr-public"
    vpc_id = aws_vpc.main_vpc.id
    description = "Security Group for use in public subnet of WIBL manager app"

    tags = {
      Name = "wibl-mgr-public"
    }
}

resource "aws_vpc_security_group_ingress_rule" "public_sg_rule1" {
  security_group_id = aws_security_group.pubic_sg.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 80
  ip_protocol = "tcp"
  to_port     = 80
}

resource "aws_vpc_security_group_ingress_rule" "public_sg_rule2" {
  security_group_id = aws_security_group.pubic_sg.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 443
  ip_protocol = "tcp"
  to_port     = 443
}

resource "aws_subnet" "private_subnet_1" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.0.0/24"
    availability_zone = "us-east-1b"
    tags = {
      Name = "wibl-private-ecs"
    }
}

resource "aws_route_table" "private_route_table" {
    vpc_id = aws_vpc.main_vpc.id

    tags = {
        Name = "wibl-private-ecs"
    }

    route {
      cidr_block = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat_gateway.id
    }
}

resource "aws_route_table_association" "private1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_route_table.id
}

resource "aws_security_group" "private_sg" {
    name = "wibl-mgr-ecs-fargate"
    vpc_id = aws_vpc.main_vpc.id
    description = "Security Group for WIBL Manager/Frontend on ECS Fargate"

    tags = {
      Name = "wibl-mgr-ecs-fargate"
    }
}

resource "aws_vpc_security_group_ingress_rule" "private_sg_rule" {
  security_group_id = aws_security_group.private_sg.id

  cidr_ipv4   = "10.0.0.0/16"
  from_port   = 8000
  ip_protocol = "tcp"
  to_port     = 8000
  tags = {
    Name = "wibl-frontend-elb"
  }
}

resource "aws_vpc_security_group_ingress_rule" "private_sg_rule2" {
  security_group_id = aws_security_group.private_sg.id

  cidr_ipv4   = "10.0.0.0/16"
  from_port   = 80
  ip_protocol = "tcp"
  to_port     = 80
  tags = {
    Name = "wibl-manager-http"
  }
}

resource "aws_vpc_security_group_ingress_rule" "private_sg_rule3" {
  security_group_id = aws_security_group.private_sg.id

  cidr_ipv4   = "10.0.0.0/16"
  from_port   = 443
  ip_protocol = "tcp"
  to_port     = 443
  tags = {
    Name = "wibl-manager-vpc-svc"
  }
}

resource "aws_vpc_endpoint" "vpc_s3_endpoint" {
    vpc_id = aws_vpc.main_vpc.id
    service_name = "com.amazonaws.us-east-1.s3"
    route_table_ids = [aws_route_table.private_route_table.id]
    tags = {
        Name = "ecs-s3"
    }
}

# Hard coded for us-east-1
data "aws_prefix_list" "s3" {
  name = "com.amazonaws.us-east-1.s3"
}

resource "aws_vpc_security_group_ingress_rule" "private_sg_rule4" {
  security_group_id = aws_security_group.private_sg.id

  from_port   = 0
  ip_protocol = "tcp"
  to_port     = 65535
  prefix_list_id = data.aws_prefix_list.s3.id

  tags = {
    Name = "wibl-ecs-s3"
  }
}

resource "aws_efs_file_system" "manager-efs" {
  creation_token = "wibl-manager-ecs-task-efs"

  encrypted = true
  performance_mode = "generalPurpose"
  throughput_mode = "bursting"
  tags = {
    Name = "wibl-manager-ecs-task-efs"
  }
}

resource "aws_efs_backup_policy" "bp1" {
  file_system_id = aws_efs_file_system.manager-efs.id

  backup_policy {
    status = "ENABLED"
  }
}

resource "aws_efs_file_system" "fronted-efs" {
  creation_token = "wibl-frontend-ecs-task-efs"

  encrypted = true
  performance_mode = "generalPurpose"
  throughput_mode = "bursting"
  tags = {
    Name = "wibl-frontend-ecs-task-efs"
  }
}

resource "aws_efs_backup_policy" "bp2" {
  file_system_id = aws_efs_file_system.fronted-efs.id

  backup_policy {
    status = "ENABLED"
  }
}

resource "aws_efs_mount_target" "mount_manager" {
  file_system_id = aws_efs_file_system.manager-efs.id
  subnet_id = aws_subnet.private_subnet_1.id
  security_groups = [aws_security_group.private_sg.id]
}

resource "aws_efs_mount_target" "mount_frontend" {
  file_system_id = aws_efs_file_system.fronted-efs.id
  subnet_id = aws_subnet.private_subnet_1.id
  security_groups = [aws_security_group.private_sg.id]
}

resource "aws_vpc_security_group_ingress_rule" "private_sg_rule5" {
  security_group_id = aws_security_group.private_sg.id

  cidr_ipv4 = "10.0.0.0/16"
  from_port   = 2049
  ip_protocol = "tcp"
  to_port     = 2049

  tags = {
    Name = "wibl-manager-efs-mount-point"
  }
}