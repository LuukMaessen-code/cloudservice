provider "aws" {
  region = var.aws_region
}

locals {
  tags = {
    Project = "cloudservice-demo"
  }
}

data "aws_availability_zones" "available" {}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = local.tags
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.8"

  cluster_name    = var.cluster_name
  cluster_version = var.eks_version

  cluster_endpoint_public_access = true

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  enable_irsa              = true
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  eks_managed_node_groups = {
    default = {
      desired_size   = var.node_desired_capacity
      min_size       = var.node_min_capacity
      max_size       = var.node_max_capacity
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"
    }
  }

  tags = local.tags
}

# Optional: uncomment to allow kubernetes/helm providers after cluster is up
# provider "kubernetes" {
#   host                   = module.eks.cluster_endpoint
#   cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
#   token                  = data.aws_eks_cluster_auth.this.token
# }
#
# data "aws_eks_cluster_auth" "this" {
#   name = module.eks.cluster_name
# }

