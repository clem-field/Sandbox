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
## Outstanding work before functional

- [ ] RDS to attach Vulcan and Heimdall
- [ ] Environment variables for Heimdall
- [ ] Environment variables for Vulcan
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
    A --> |HTTPS| B 
    subgraph ECS 
    B --> |HTTP| C
    B --> |HTTP| D
    end
```