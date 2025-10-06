resource "aws_vpc" "wibl-upload-server-vpc" {
  cidr_block = var.vpc_cidr
  tags = {
    Name = "wibl-upload-server"
  }
}
