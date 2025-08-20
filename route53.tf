# Route 53 Hosted Zone for risk-sentinel.info
resource "aws_route53_zone" "main" {
  name = var.domain_name
  tags = { Name = "risk-sentinel-hosted-zone" }
}

# A Record pointing to ALB (for ECS Fargate setup)
resource "aws_route53_record" "alb" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name  # risk-sentinel.info
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name  # From alb.tf
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# Optional CNAME for vulcan subdomain
resource "aws_route53_record" "vulcan" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "vulcan.${var.domain_name}"  # vulcan.risk-sentinel.info
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.main.dns_name]
}

# Optional CNAME for heimdall subdomain
resource "aws_route53_record" "heimdall" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "heimdall.${var.domain_name}"  # heimdall.risk-sentinel.info
  type    = "CNAME"
  ttl     = 300
  records = [aws_lb.main.dns_name]
}