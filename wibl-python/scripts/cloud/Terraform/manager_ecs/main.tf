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
  force_delete = true
}

# Create manager repo
resource "aws_ecr_repository" "manager_ecr_repo" {
  name                 = "wibl/manager"
  force_delete = true
}

# Build frontend image and push to ECR repo
resource "docker_image" "frontend_image" {
  name         = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/frontend:latest"
  build {
    context    = "${var.src_path}/wibl-frontend"
    platform   = "linux/${var.architecture}"
  }
  triggers = {
    source_hash = sha1(join("", [
      for f in fileset("${var.src_path}/wibl-frontend", "**/*") :
      filemd5("${var.src_path}/wibl-frontend/${f}")
    ]))
  }
}

resource "docker_registry_image" "frontend" {
  name = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/frontend:latest"
  keep_remotely = true
  depends_on = [aws_ecr_repository.frontend_ecr_repo, docker_image.frontend_image]
}

# Build manager image and push to ECR repo
resource "docker_image" "manager_image" {
  name         = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/manager:latest"
  build {
    context    = "${var.src_path}/wibl-manager"
    platform   = "linux/${var.architecture}"
  }
  triggers = {
    source_hash = sha1(join("", [
      for f in fileset("${var.src_path}/wibl-manager", "**/*") :
      filemd5("${var.src_path}/wibl-manager/${f}")
    ]))
  }
}

resource "docker_registry_image" "manager" {
  name = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/manager:latest"
  keep_remotely = true
  depends_on = [aws_ecr_repository.manager_ecr_repo, docker_image.manager_image]
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

resource "aws_subnet" "private_subnet_2" {
    vpc_id = aws_vpc.main_vpc.id
    cidr_block = "10.0.1.0/24"
    availability_zone = "${var.region}a"
    tags = {
      Name = "wibl-private-ecs2"
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

resource "aws_route_table_association" "private2" {
  subnet_id      = aws_subnet.private_subnet_2.id
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

# Allow the vpc to send out towards the things it needs to.
resource "aws_vpc_security_group_egress_rule" "private_sg_egress" {
  security_group_id = aws_security_group.private_sg.id

  ip_protocol = "-1"
  cidr_ipv4 = "0.0.0.0/0"
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

# Ripped out the EFS, no more Phase 3


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
resource "aws_lb" "wibl_manager" {
  name               = "wibl-manager-ecs-elb"
  internal           = true
  load_balancer_type = "network"
  subnets            = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
}
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
  load_balancer_arn = aws_lb.wibl_manager.arn
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
    type = "fixed-response"

    fixed_response {
      status_code  = "403"
      content_type = "text/plain"
      message_body = "Forbidden"
    }
  }
}

resource "aws_lb_listener_rule" "require_header" {
  listener_arn = aws_lb_listener.frontend_listener.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend_tg.arn
  }

  condition {
    http_header {
      http_header_name = "X-Origin-Verify"
      values           = [var.origin_secret]
    }
  }
}

resource "aws_security_group" "private_rds_sg" {
  name = "wibl-rds"
  vpc_id = aws_vpc.main_vpc.id
  description = "Security Group for the WIBL Manager/Frontend RDS Postgres databases"

  tags = {
    Name = "wibl-rds"
  }
}

# First create the RDS instance for the manager, and all of the vpc setup
resource "aws_vpc_security_group_ingress_rule" "private_rds_sg_rule1" {
  ip_protocol       = "tcp"
  from_port = 5432
  to_port = 5432
  security_group_id = aws_security_group.private_rds_sg.id
  referenced_security_group_id = aws_security_group.private_sg.id
}

resource "aws_vpc_security_group_egress_rule" "private_rds_sg_rule2" {
  ip_protocol       = "-1"
  security_group_id = aws_security_group.private_rds_sg.id
  from_port = 0
  to_port = 0
  cidr_ipv4 = "0.0.0.0/0"
}

resource "aws_db_subnet_group" "manager_db_subnet_group" {
  name = "manager_db_subnet_group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
  tags = {
    Name = "manager_db_subnet_group"
  }
}

resource "aws_db_instance" "manager_db_instance" {
  allocated_storage    = var.manager_db_size
  db_name              = var.manager_db_name
  engine               = "postgres"
  engine_version = "17"
  instance_class       = "db.t4g.micro"
  username             = var.manager_db_user
  password             = var.manager_db_password
  skip_final_snapshot = true
  db_subnet_group_name = aws_db_subnet_group.manager_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.private_rds_sg.id]
  tags = {
    Name = var.manager_db_name
  }
  publicly_accessible = false
}

resource "aws_db_instance" "frontend_db_instance" {
  allocated_storage    = var.frontend_db_size
  db_name              = var.frontend_db_name
  engine               = "postgres"
  instance_class       = "db.t4g.micro"
  username             = var.frontend_db_user
  password             = var.frontend_db_password
  skip_final_snapshot = true
  db_subnet_group_name = aws_db_subnet_group.manager_db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.private_rds_sg.id]
  tags = {
    Name = var.frontend_db_name
  }
  publicly_accessible = false
}

# Create one off ECS tasks for frontend and manager setup

# Create a cloudwatch group for the managers setup
resource "aws_cloudwatch_log_group" "manager_setup" {
  name              = "/ecs/manager_setup"
  retention_in_days = 14
}

# Create a cloudwatch group for the frontends setup
resource "aws_cloudwatch_log_group" "frontend_setup" {
  name = "/ecs/frontend_setup"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "frontend_setup" {
  family                   = "frontend_setup"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  memory                   = 512
  cpu                      = 256
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_frontend_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([{
    name      = "frontend_setup"
    image     = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/frontend:latest"
    essential = true
    command   = ["bash", "-c", <<EOT
      set -e
      echo "Running migrations..."
      python manage.py migrate
      echo "Creating superuser..."
      python manage.py create_superuser
      echo "Collecting static files..."
      python manage.py collectstatic --noinput
EOT
    ]
    environment = [
      { name = "FRONTEND_DATABASE_NAME", value = var.frontend_db_name },
      { name = "FRONTEND_DATABASE_USER", value = var.frontend_db_user },
      { name = "FRONTEND_DATABASE_PASSWORD", value = var.frontend_db_password },
      { name = "FRONTEND_DATABASE_HOST", value = aws_db_instance.frontend_db_instance.address },
      { name = "SUPERUSER_USERNAME", value = var.superuser_username},
      { name = "SUPERUSER_PASSWORD", value = var.superuser_password},
      { name = "FRONTEND_SECRET_KEY", value = var.frontend_secret_key},
      { name = "DEBUG_MODE", value = var.debug_mode},
      { name = "STATIC_BUCKET_NAME", value = var.static_bucket_name},
      { name = "AWS_REGION", value = var.region},
      { name = "ALB_DNS_NAME", value = aws_lb.frontend_alb.dns_name}
    ]
    logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/frontend_setup"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
  }])
}

resource "null_resource" "run_frontend_setup" {
  depends_on = [aws_ecs_task_definition.frontend_setup, aws_cloudwatch_log_group.frontend_setup, aws_db_instance.frontend_db_instance]

  provisioner "local-exec" {
    command = <<EOT
aws ecs run-task \
  --region ${var.region} \
  --cluster ${aws_ecs_cluster.wibl_manager.id} \
  --launch-type FARGATE \
  --task-definition ${aws_ecs_task_definition.frontend_setup.family} \
  --network-configuration "awsvpcConfiguration={subnets=[${aws_subnet.private_subnet_1.id},${aws_subnet.private_subnet_2.id}],securityGroups=[${aws_security_group.private_sg.id}],assignPublicIp=DISABLED}"
EOT
  }
}

resource "aws_ecs_task_definition" "manager_setup" {
  family                   = "manager_setup"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn

  cpu    = 256
  memory = 512

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = "manager_setup"
      image     = "${var.account_number}.dkr.ecr.${var.region}.amazonaws.com/wibl/manager:latest"
      essential = true

      command = [
        "bash", "-c",
        <<EOT
set -e
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."
EOT
      ]

      environment = [
        {
          name  = "MANAGER_DATABASE_URI"
          value = "postgresql+psycopg://${var.manager_db_user}:${var.manager_db_password}@${aws_db_instance.manager_db_instance.address}:5432/${var.manager_db_name}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/manager_setup"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "null_resource" "run_manager_migrations" {
  depends_on = [
    aws_ecs_task_definition.manager_setup,
    aws_db_instance.manager_db_instance,
    aws_cloudwatch_log_group.manager_setup
  ]

  provisioner "local-exec" {
    command = <<EOT
aws ecs run-task \
  --region ${var.region} \
  --cluster ${aws_ecs_cluster.wibl_manager.id} \
  --launch-type FARGATE \
  --task-definition ${aws_ecs_task_definition.manager_setup.family} \
  --network-configuration "awsvpcConfiguration={subnets=[${aws_subnet.private_subnet_1.id},${aws_subnet.private_subnet_2.id}],securityGroups=[${aws_security_group.private_sg.id}],assignPublicIp=DISABLED}"
EOT
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled = true

  origin {
    domain_name = aws_lb.frontend_alb.dns_name
    origin_id   = "alb-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    custom_header {
      name  = "X-Origin-Verify"
      value = var.origin_secret
    }
  }

  default_cache_behavior {
    target_origin_id       = "alb-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = true

      cookies {
        forward = "all"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}


# Using images pushed to ECR above, create task definitions
# Instantiate wibl-manager task definition from template and register task with ECS

# Manager Task Definition
resource "aws_ecs_task_definition" "wibl_manager" {
  family                   = "wibl-manager"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  cpu = 256
  memory = 512

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture = "ARM64"
  }

  # Decode the JSON template after variable substitution
  container_definitions = (
    templatefile("${var.src_path}/scripts/cloud/AWS/manager/input/terraform-manager-container-definition.proto", {
      REPLACEME_ACCOUNT_NUMBER = var.account_number
      REPLACEME_AWS_REGION     = var.region
      REPLACEME_DATABASE_URI    = "postgresql+psycopg://${var.manager_db_user}:${var.manager_db_password}@${aws_db_instance.manager_db_instance.address}:5432/${var.manager_db_name}"
    })
  )
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
      for b in [var.incoming_bucket_name, var.staging_bucket_name, var.viz_bucket_name, var.static_bucket_name] : [
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
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn = aws_iam_role.ecs_frontend_task_role.arn
  memory = 512
  cpu = 256

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture = "ARM64"
  }

  # Decode the JSON template after variable substitution
  container_definitions = (
    templatefile("${var.src_path}/scripts/cloud/AWS/manager/input/terraform-frontend-container-definition.proto", {
      REPLACEME_ACCOUNT_NUMBER     = var.account_number
      REPLACEME_AWS_REGION         = var.region
      REPLACEME_MANAGEMENT_URL     = "http://${aws_lb.wibl_manager.dns_name}"

      REPLACEME_INCOMING_BUCKET    = var.incoming_bucket_name
      REPLACEME_STAGING_BUCKET     = var.staging_bucket_name
      REPLACEME_VIZ_BUCKET         = var.viz_bucket_name
      REPLACEME_VIZ_LAMBDA         = var.viz_lambda_name
      REPLACEME_STATIC_BUCKET      = var.static_bucket_name

      REPLACEME_DATABASE_NAME      = var.frontend_db_name
      REPLACEME_DATABASE_USER      = var.frontend_db_user
      REPLACEME_DATABASE_PASSWORD  = var.frontend_db_password
      REPLACEME_DATABASE_HOST      = aws_db_instance.frontend_db_instance.address

      REPLACEME_SUPERUSER_USERNAME = var.superuser_username
      REPLACEME_SUPERUSER_PASSWORD = var.superuser_password

      REPLACEME_SECRET_KEY         = var.frontend_secret_key
      REPLACEME_DEBUG_MODE         = var.debug_mode

      REPLACEME_ALB_DNS            = aws_cloudfront_distribution.frontend.domain_name
    })
  )
}

# Manager ECS Service
resource "aws_ecs_service" "wibl_manager" {
  name            = "wibl-manager-ecs-svc"
  cluster         = aws_ecs_cluster.wibl_manager.id
  task_definition = aws_ecs_task_definition.wibl_manager.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  force_new_deployment = true

  network_configuration {
    subnets         = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    security_groups = [aws_security_group.private_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.manager_tg.arn
    container_name   = "wibl-manager"
    container_port   = 8000
  }

  depends_on = [aws_lb_target_group.manager_tg, null_resource.run_manager_migrations]
}

# Frontend ECS Service
resource "aws_ecs_service" "wibl_frontend" {
  name            = "wibl-frontend-ecs-svc"
  cluster         = aws_ecs_cluster.wibl_manager.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  force_new_deployment = true

  network_configuration {
    subnets         = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    security_groups = [aws_security_group.private_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend_tg.arn
    container_name   = "wibl-frontend"
    container_port   = 8000
  }

  depends_on = [aws_lb_target_group.frontend_tg, null_resource.run_frontend_setup]
}


