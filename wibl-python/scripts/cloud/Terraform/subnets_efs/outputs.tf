output "public_subnet1" {
    value = aws_subnet.public_subnet_1.arn
}

output "public_subnet2" {
    value = aws_subnet.public_subnet_2.arn
}

output "private_subnet" {
    value = aws_subnet.private_subnet_1.arn
}

output "private_sg" {
    value = aws_security_group.private_sg.arn
}