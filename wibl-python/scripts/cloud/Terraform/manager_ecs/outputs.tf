output "public_subnet1" {
    value = aws_subnet.public_subnet_1.id
}

output "public_subnet2" {
    value = aws_subnet.public_subnet_2.id
}

output "private_subnet" {
    value = aws_subnet.private_subnet_1.id
}

output "private_sg" {
    value = aws_security_group.private_sg.id
}

output "private_rds_sg_id" {
    value = aws_security_group.private_rds_sg.id
}

output "manager_db_subnet_group_name" {
    value = aws_db_subnet_group.manager_db_subnet_group.name
}

output "manager_url" {
    value = "http://${aws_lb.wibl_manager.dns_name}"
}