# Sandbox

## Purpose

The Sandbox is exactly as it sounds. It is a repo for testing services and development storage.

<strong>Important: Do not rely on this repo to be stable as code is moved in and out of it.</strong>

```mermaid
---
config:
    theme: redux
---
flowchart TD
    A["`Build Images
    Heimdall2:latest
    Vulcan:latest
    custom-nginx:latest`"]
    A --> B["`Run Terraform Apply
    This will build:
    ECR's - vulcan, heimdall, and nginx
    ECS - 1 Task, 3 containers
    Route53
    ALB - HTTPS and reroute from HTTP
    IAM - basic roles`"]
    B --> |pending images in ECR| C["`ECS will start:
    Need to push images to ECR before it will succeed`"]
```
## Work to make it functional

- [x] Create the ECR
- [x] Re-tag images
- [x] Route53 Transfer of risk-sentinel - in-progress
- [ ] Update ECS permissions for retrieving the images
- [x] RDS to attach Vulcan and Heimdall
- [x] Environment variables for Heimdall
- [x] Environment variables for Vulcan
- [ ] Validate NGINX has HTTPS and Reverse Proxy

## Desired Function

```mermaid
---
config:
    theme: redux
---
flowchart LR
    A["`ALB`"]
    B["`NGINX`"]
    C["`vulcan.risk-sentinel.info`"]
    D["`heimdall.risk-sentinel.info`"]
    E["`RDS PostgreSQL`"]
    F["`Secrets Manager`"]
    f["`KMS`"]
    G["`Okta`"]
    A <--> |HTTPS| B 
    subgraph ECS 
    B <--> |HTTP| C
    B <--> |HTTP| D
    end
    subgraph RDS
    C <--> | SSL | E
    D <--> | SSL | E
    end
    B <--> | HTTPS | G
    subgraph KMS_SM
    F
    f
    end
    C <--> f <--> F
    D <--> f <--> F 
    
```