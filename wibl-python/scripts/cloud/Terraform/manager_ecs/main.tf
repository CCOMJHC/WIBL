terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
    }
    docker = {
      source  = "kreuzwerker/docker"
    }
  }
}

####################
# Phase 0: Setup ECR container registry repos and build and push container images

# Create frontend repo
resource "aws_ecr_repository" "frontend_ecr_repo" {
  name                 = "wibl/frontend"
}

# Create manager repo
resource "aws_ecr_repository" "manager_ecr_repo" {
  name                 = "wibl/manager"
}

# Build frontend image and push to ECR repo
resource "docker_image" "frontend_image" {
  name         = "wibl/frontend"
  build {
    context    = "${var.src_path}/wibl-frontend"
    platform   = "linux/${var.architecture}"
  }
  triggers = {
    dockerfile_hash = sha1(filemd5("${var.src_path}/wibl-frontend/Dockerfile"))
  }

}

resource "docker_registry_image" "frontend" {
  name = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/frontend:latest"
  keep_remotely = true
  depends_on = [aws_ecr_repository.frontend_ecr_repo]
}

# Build manager image and push to ECR repo
resource "docker_image" "manager_image" {
  name         = "wibl/manager"
  build {
    context    = "${var.src_path}/wibl-manager"
    platform   = "linux/${var.architecture}"
  }
  triggers = {
    dockerfile_hash = sha1(filemd5("${var.src_path}/wibl-manager/Dockerfile"))
  }
}

resource "docker_registry_image" "manager" {
  name = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/manager:latest"
  keep_remotely = true
  depends_on = [aws_ecr_repository.manager_ecr_repo]
}

####################
# Phase 1: Create VPC, public and private subnets and route tables, as well as security groups for ECS Fargate
#          deployment of wibl-manager and wibl-frontend.

# Create a VPC with a 10.0.0.0/16 address block
# Update enable DNS hostnames on VPC
resource "aws_vpc" "main_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
}

# Create public subnets
# Tag the subnets with a name
resource "aws_subnet" "public_subnet_1" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.2.0/24"
    availability_zone = "${var.region}b"
    tags = {
      Name = "wibl-public"
    }
}

resource "aws_subnet" "public_subnet_2" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.4.0/24"
    availability_zone = "${var.region}a"
    tags = {
      Name = "wibl-public2"
    }
}

# Create NAT gateway so the lambdas can access the Internet for submission to DCDB, and ECS can access ECR.
# Create Elastic IP to associate with NAT gateway
resource "aws_eip" "elastic_ip" {
    domain = "vpc"
}

## Create NAT gateway
# Tag NAT gateway with lambda
resource "aws_nat_gateway" "nat_gateway" {
    allocation_id = aws_eip.elastic_ip.id
    subnet_id = aws_subnet.public_subnet_1.id

    tags = {
      Name = "wibl-lambda-nat"
    }
}

# Create Internet gateway
# Tag Internet gateway with a name
# Attach the Internet gateway to the VPC
resource "aws_internet_gateway" "ig_public" {
  vpc_id = aws_vpc.main_vpc.id

  tags = {
    Name = "wibl-public"
  }
}

# Create a routing table for public subnet of the VPC
# Tag the route table with a name
# Create route pointing traffic to the Internet gateway
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

# Associate the custom routing table with the public subnets
resource "aws_route_table_association" "public1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "public2" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_route_table.id
}

# Create security group to give us control over ingress/egress
# Tag the security group with a name
resource "aws_security_group" "pubic_sg" {
    name = "wibl-mgr-public"
    vpc_id = aws_vpc.main_vpc.id
    description = "Security Group for use in public subnet of WIBL manager app"

    tags = {
      Name = "wibl-mgr-public"
    }
}

# Create PUBLIC ingress rule to the wibl-frontend load balancer to access the frontend via ports 80 and 443
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
# Create private subnet
# Tag private subnets with a name
resource "aws_subnet" "private_subnet_1" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.0.0/24"
    availability_zone = "${var.region}b"
    tags = {
      Name = "wibl-private-ecs"
    }
}

# Create a routing table for private subnets to the VPC
# Tag the route table with a name
# Update route table in private subnet to route to NAT gateway
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

# Associate the custom routing table with the private subnets:
resource "aws_route_table_association" "private1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_route_table.id
}

# Create security group to give us control over ingress/egress
# Tag the security group with a name
resource "aws_security_group" "private_sg" {
    name = "wibl-mgr-ecs-fargate"
    vpc_id = aws_vpc.main_vpc.id
    description = "Security Group for WIBL Manager/Frontend on ECS Fargate"

    tags = {
      Name = "wibl-mgr-ecs-fargate"
    }
}

# Create ingress rule so that wibl-manager and wibl-frontend load balancers can access manager and frontend via port 8000
# Tag the load balancer ingress rules with a name
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

# Create an ingress rules to allow anything running in the same VPC (e.g., ECS, lambdas, EC2) to access other
# services in the subnet via HTTPS and HTTPS (HTTPS allows access to VPC endpoints; HTTP rule only needed for accessing
# WIBL manager via ELB)
# Tag the HTTP/HTTPS ingress rules with names
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

# Create service endpoint so that things running in the VPC can access S3
resource "aws_vpc_endpoint" "vpc_s3_endpoint" {
    vpc_id = aws_vpc.main_vpc.id
    service_name = "com.amazonaws.${var.region}.s3"
    route_table_ids = [aws_route_table.private_route_table.id]
    tags = {
        Name = "ecs-s3"
    }
}

data "aws_prefix_list" "s3" {
  name = "com.amazonaws.${var.region}.s3"
}

# Create ingress rule to allow all connections from AWS_REGION_S3_PL (region-specific S3 CIDR blocks)
# Tag the S3 ingress rule with name
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

####################
# Phase 3: Create EFS volumes and mount points for private subnet

# Create the volumes
# Note: Make sure your account has the `AmazonElasticFileSystemFullAccess` permissions policy
# attached to it.
# wibl-manager volume

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

# wibl-frontend volume
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

# Create mount targets for EFS volume within our VPC subnet
# wibl-manager mount target
resource "aws_efs_mount_target" "mount_manager" {
  file_system_id = aws_efs_file_system.manager-efs.id
  subnet_id = aws_subnet.private_subnet_1.id
  security_groups = [aws_security_group.private_sg.id]
}
# wibl-frontend mount target 1 (in first subnet in the AZ)
resource "aws_efs_mount_target" "mount_frontend" {
  file_system_id = aws_efs_file_system.fronted-efs.id
  subnet_id = aws_subnet.private_subnet_1.id
  security_groups = [aws_security_group.private_sg.id]
}

# Create ingress rule to allow NFS connections from the subnet (e.g., EFS mount points)
# Tag the NFS ingress rule with a name:
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

####################
# Phase 4: Setup ECS cluster and task definitions

# Create cluster
resource "aws_ecs_cluster" "wibl_manager" {
  name                = "wibl-manager-ecs"
  tags = {
    Name = "wibl-manager-ecs"
  }
}

resource "aws_ecs_cluster_capacity_providers" "capacity_attach" {
  cluster_name = aws_ecs_cluster.wibl_manager.name
  capacity_providers = ["FARGATE"]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
  }
}

# Setup 'ecsTaskExecutionRole' role and attach relevant policies
# Create `ecsTaskExecutionRole`
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"
  assume_role_policy = file("${var.src_path}/scripts/cloud/AWS/manager/input/task-execution-assume-role.json")
}

# Next, attach role policy
resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Associate CloudWatch policy to `ecsInstanceRole` to allow ECS tasks to send logs to CloudWatch
# Create policy
resource "aws_iam_policy" "ecs_cloudwatch_logs" {
  name   = "ECS-CloudWatchLogs"
  policy = file("${var.src_path}/scripts/cloud/AWS/manager/input/ecs-cloudwatch-policy.json")
}

# Attach policy to ECS role
resource "aws_iam_role_policy_attachment" "ecs_cloudwatch_logs_attach" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_cloudwatch_logs.arn
}

# Create load balancers so that lambdas can find wibl-manager and wibl-frontend services
# Create internal NETWORK load balancer for wibl-manager
# Tag the security group with a name
resource "aws_security_group" "fe_elb_public" {
  name        = "wibl-fe-elb-public"
  description = "Security Group for WIBL frontend load balancer"
  vpc_id      = aws_vpc.main_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port                = 8000
    to_port                  = 8000
    protocol                 = "tcp"
    security_groups          = [aws_security_group.private_sg.id]
  }

  tags = {
    Name = "wibl-fe-elb-public"
  }
}

# Finally create the internet-facing wibl-frontend APPLICATION load balancer
resource "aws_lb" "frontend_alb" {
  name               = "wibl-frontend-ecs-elb"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
  security_groups    = [aws_security_group.fe_elb_public.id]

  tags = {
    Name = "wibl-frontend-ecs-elb"
  }
}

# wibl-frontend target group
resource "aws_lb_target_group" "frontend_tg" {
  name                 = "wibl-frontend-ecs-elb-tg"
  port                 = 8000
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.main_vpc.id
  health_check {
    protocol = "HTTP"
    path     = "/heartbeat"
    port     = "8000"
  }
}

# wibl-manager target group
resource "aws_lb_target_group" "manager_tg" {
  name        = "wibl-manager-ecs-elb-tg"
  port        = 8000
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = aws_vpc.main_vpc.id
}

# Create ELB listeners

# wibl-manager listener
resource "aws_lb_listener" "manager_listener" {
  load_balancer_arn = aws_lb.frontend_alb.arn
  port              = 80
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.manager_tg.arn
  }
}

# wibl-frontend TLS listener
resource "aws_lb_listener" "frontend_listener" {
  load_balancer_arn = aws_lb.frontend_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend_tg.arn
  }
}

# Using images pushed to ECR above, create task definitions
# Instantiate wibl-manager task definition from template and register task with ECS

# Manager Task Definition
resource "aws_ecs_task_definition" "wibl_manager" {

  family                   = "wibl-manager"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  # Decode the JSON template after variable substitution
  container_definitions = jsonencode([jsondecode(
      templatefile("${var.src_path}/scripts/cloud/AWS/manager/input/manager-task-definition.proto", {
        REPLACEME_ACCOUNT_NUMBER = var.account_number
        REPLACEME_AWS_EFS_FS_ID  = aws_efs_file_system.manager-efs.id
        REPLECEME_AWS_REGION     = var.region
      })
    )
  ])
}

# Frontend ECS task role
resource "aws_iam_role" "ecs_frontend_task_role" {
  name = "ecsFrontEndTaskRole"
  assume_role_policy = file("${var.src_path}/scripts/cloud/AWS/manager/input/task-execution-assume-role.json")
}

# Allow frontend ECS task role to access S3 buckets
data "aws_iam_policy_document" "frontend_s3_access" {
  statement {
    sid    = "FrontendAllowS3AccessAll"
    effect = "Allow"
    actions = ["s3:*"]

    resources = flatten([
      for b in [var.incoming_bucket_name, var.staging_bucket_name, var.viz_bucket_name] : [
        "arn:aws:s3:::${b}",
        "arn:aws:s3:::${b}/*"
      ]
    ])
  }
}

resource "aws_iam_role_policy" "frontend_s3_access_all" {
  name   = "frontend-s3-access-all"
  role   = aws_iam_role.ecs_frontend_task_role.id
  policy = data.aws_iam_policy_document.frontend_s3_access.json
}

# Allow frontend task to invoke the visualization lambda
data "aws_iam_policy_document" "frontend_invoke_vizlambda" {
  statement {
    sid    = "FrontendAllowVizLambdaInvoke"
    effect = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [
      "arn:aws:lambda:${var.region}:${var.account_number}:function:${var.viz_lambda_name}"
    ]
  }
}

resource "aws_iam_role_policy" "frontend_invoke_vizlambda" {
  name   = "frontend-invoke-vizlambda"
  role   = aws_iam_role.ecs_frontend_task_role.id
  policy = data.aws_iam_policy_document.frontend_invoke_vizlambda.json
}

# Frontend Task Definition
resource "aws_ecs_task_definition" "frontend" {
  family                   = "wibl-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  task_role_arn = aws_iam_role.ecs_frontend_task_role.arn
  # Decode the JSON template after variable substitution
  container_definitions = jsonencode([
    jsondecode(
      templatefile("${var.src_path}/scripts/cloud/AWS/manager/input/frontend-task-definition.proto", {
        REPLACEME_ACCOUNT_NUMBER  = var.account_number
        REPLACEME_AWS_EFS_FS_ID   = aws_efs_file_system.fronted-efs.id
        REPLECEME_AWS_REGION      = var.region
        REPLACEME_MANAGEMENT_URL  = "http://${aws_lb.frontend_alb.dns_name}"
        REPLACEME_INCOMING_BUCKET = var.incoming_bucket_name
        REPLACEME_STAGING_BUCKET  = var.staging_bucket_name
        REPLACEME_VIZ_BUCKET      = var.viz_bucket_name
        REPLACEME_VIZ_LAMBDA      = var.viz_lambda_name
      })
    )
  ])
}

# Manager ECS Service
resource "aws_ecs_service" "wibl_manager" {
  name            = "wibl-manager-ecs-svc"
  cluster         = aws_ecs_cluster.wibl_manager.id
  task_definition = aws_ecs_task_definition.wibl_manager.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_subnet_1.id]
    security_groups = [aws_security_group.private_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.manager_tg.arn
    container_name   = "wibl-manager"
    container_port   = 8000
  }

  depends_on = [aws_lb_target_group.manager_tg]
}

# Frontend ECS Service
resource "aws_ecs_service" "wibl_frontend" {
  name            = "wibl-frontend-ecs-svc"
  cluster         = aws_ecs_cluster.wibl_manager.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_subnet_1.id]
    security_groups = [aws_security_group.private_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend_tg.arn
    container_name   = "wibl-frontend"
    container_port   = 8000
  }

  depends_on = [aws_lb_target_group.frontend_tg]
}

