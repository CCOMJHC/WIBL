resource "aws_subnet" "public" {
  vpc_id                  = var.vpc_id
  cidr_block              = var.cidr_block
  map_public_ip_on_launch = true
  tags = {
    Name = "wibl-upload-server-public-subnet"
  }
}
