resource "aws_instance" "web" {
  ami           = var.upload_server_ami
  instance_type = "t3.micro"

  # assign it a public ip so we can connect to it
  associate_public_ip_address = true

  # references security group created below
  vpc_security_group_ids = [aws_security_group.sg.id]

  lifecycle {
    replace_triggered_by = [aws_security_group.sg]
  }

  # subnet to launch the instance in
  subnet_id = aws_subnet.public.id

  # simple server running on port 80 so we can verify
  # that the instance is up and we can connect to it
  user_data = <<-EOF
              #!/bin/bash
              echo "Hello, World" > index.html
              nohup busybox httpd -f -p "80" &
              EOF
}
