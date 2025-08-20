terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~>6.9.0"
    }
  }
  required_version = ">= 1.13.0"
}

provider "aws" {
  region = var.region
  profile = "default"
}

# Add modules here