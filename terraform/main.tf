provider "aws" {
  region = var.region
}

# Orchestrate resources (no need for modules here, but could extend to child modules)