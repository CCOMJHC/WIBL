output "public_dns" {
  value = aws_eip.public_ip.public_dns
}

output "public_ip" {
  value = aws_eip.public_ip.public_ip
}

output "id" {
  value = aws_eip.public_ip.id
}