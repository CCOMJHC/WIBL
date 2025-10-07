output "upload_bucket_arn" {
  value = aws_s3_bucket.upload_bucket.arn
}

output "upload_topic_arn" {
  value = aws_sns_topic.upload_topic.arn
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

output "subnet_cidr" {
  description = "CIDR block of the public subnet"
  value       = aws_subnet.public.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.ec2_instance.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.ec2_instance.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.ec2_instance.private_ip
}

output "ssh_key_name" {
  description = "Name of the SSH key pair"
  value       = aws_key_pair.ec2_key_pair.key_name
}

output "ssh_private_key_path" {
  description = "Path to the private SSH key file"
  value       = local_file.private_key.filename
}

output "ssh_connection_command" {
  description = "Command to SSH into the instance"
  value       = "ssh -i ${local_file.private_key.filename} ec2-user@${aws_instance.ec2_instance.public_ip}"
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.wibl_upload_server.id
}
