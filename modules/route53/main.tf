resource "aws_route53_zone" "main" {
  name = var.domain_name
  tags = { Name = "risk-sentinel-hosted-zone" }
}

resource "aws_route53_record" "alb" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "vulcan" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "vulcan.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [var.alb_dns_name]
}

resource "aws_route53_record" "heimdall" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "heimdall.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = [var.alb_dns_name]
}