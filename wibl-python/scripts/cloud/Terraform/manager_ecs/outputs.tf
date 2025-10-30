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