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

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

############################
# Security Group
############################

resource "aws_security_group" "jenkins_sg" {
  name        = "jenkins-sg-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  description = "Security group for Jenkins Controller"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Jenkins UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "Jenkins-SG"
  }
}

############################
# SSH Key Pair (NEW)
############################

resource "aws_key_pair" "jenkins_key" {
  key_name   = "jenkins-new-key"
  public_key = file("~/.ssh/jenkins-new-key.pub")

  tags = {
    Name = "Jenkins New Key"
  }
}

############################
# EC2 Jenkins Controller
############################

resource "aws_instance" "jenkins_controller" {
  ami           = "ami-0557a15b87f6559cf" # Amazon Linux 2
  instance_type = "t2.medium"
  subnet_id     = data.aws_subnet.default.id
  key_name      = aws_key_pair.jenkins_key.key_name

  vpc_security_group_ids = [
    aws_security_group.jenkins_sg.id
  ]

  associate_public_ip_address = true

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name = "Jenkins-Controller"
  }

  user_data = <<-EOF
    #!/bin/bash
    yum update -y

    # Java
    amazon-linux-extras install java-openjdk11 -y

    # Jenkins
    wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
    rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
    yum install jenkins -y

    sed -i 's/JENKINS_ARGS=""/JENKINS_ARGS="--httpListenAddress=0.0.0.0"/' /etc/sysconfig/jenkins

    systemctl enable jenkins
    systemctl start jenkins

    # Git & Docker
    yum install git docker -y
    systemctl start docker
    systemctl enable docker
    usermod -aG docker jenkins

    systemctl restart jenkins
  EOF
}

############################
# Elastic IP
############################

resource "aws_eip" "jenkins_eip" {
  domain = "vpc"

  tags = {
    Name = "Jenkins-EIP"
  }
}

resource "aws_eip_association" "jenkins_eip_assoc" {
  instance_id   = aws_instance.jenkins_controller.id
  allocation_id = aws_eip.jenkins_eip.id
}

############################
# Outputs
############################

output "jenkins_public_ip" {
  value = aws_eip.jenkins_eip.public_ip
}

output "jenkins_url" {
  value = "http://${aws_eip.jenkins_eip.public_ip}:8080"
}

output "ssh_command" {
  value = "ssh -o IdentitiesOnly=yes -i ~/.ssh/jenkins-new-key ec2-user@${aws_eip.jenkins_eip.public_ip}"
}

output "password_command" {
  value = "ssh -i ~/.ssh/jenkins-new-key ec2-user@${aws_eip.jenkins_eip.public_ip} 'sudo cat /var/lib/jenkins/secrets/initialAdminPassword'"
}
