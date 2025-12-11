variable "aws_region" {
  description = "AWS region to deploy the EKS cluster into"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name for the EKS cluster"
  type        = string
  default     = "cloudservice-demo"
}

variable "eks_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
}

variable "node_instance_types" {
  description = "EC2 instance types for the default node group"
  type        = list(string)
  default     = ["t3.small"]
}

variable "node_desired_capacity" {
  description = "Desired node count"
  type        = number
  default     = 2
}

variable "node_min_capacity" {
  description = "Minimum node count"
  type        = number
  default     = 1
}

variable "node_max_capacity" {
  description = "Maximum node count"
  type        = number
  default     = 4
}

