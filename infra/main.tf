provider "aws" {
  region = "us-east-1"
}

############################
# Default VPC & Subnet
############################

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "default" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = "us-east-1a"
}

############################
# Existing Security Group
############################

data "aws_security_group" "jenkins_sg" {
  name   = "jenkins-sg-final"
  vpc_id = data.aws_vpc.default.id
}

############################
# EC2 Jenkins Controller
############################

resource "aws_instance" "jenkins_controller" {
  ami           = "ami-0557a15b87f6559cf"
  instance_type = "t2.medium"
  subnet_id     = data.aws_subnet.default.id

  key_name = "jenkins-terraform-key"

  vpc_security_group_ids = [
    data.aws_security_group.jenkins_sg.id
  ]

  associate_public_ip_address = true

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    amazon-linux-extras install java-openjdk11 -y
    wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
    rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
    yum install jenkins -y
    systemctl enable jenkins
    systemctl start jenkins
  EOF

  tags = {
    Name = "Jenkins-Controller-test"
  }
}

############################
# Outputs
############################

output "ssh_command" {
  value = "ssh -o IdentitiesOnly=yes -i ~/.ssh/jenkins-terraform-key.pem ec2-user@${aws_instance.jenkins_controller.public_ip}"
}

output "jenkins_url" {
  value = "http://${aws_instance.jenkins_controller.public_ip}:8080"
}
