terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# SNS Topic for alerts
resource "aws_sns_topic" "health_alerts" {
  name = "aws_health_alerts"
}

# Email subscription (requires manual confirmation)
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.health_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# EventBridge Rule (formerly CloudWatch Events)
resource "aws_cloudwatch_event_rule" "health_events" {
  name        = "aws-health-to-sns"
  description = "Captures AWS Health events for selected services"

  event_pattern = jsonencode({
    source      = ["aws.health"]
    detail-type = ["AWS Health Event"]
    detail = {
      eventTypeCategory = var.event_categories
      service           = var.services
    }
  })
}

# Target: Send to SNS with formatted message
resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.health_events.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.health_alerts.arn

  input_transformer {
    input_paths = {
      description = "$.detail.eventDescription[0].latestDescription"
      service     = "$.detail.service"
      category    = "$.detail.eventTypeCategory"
      time        = "$.time"
    }

    input_template = <<EOF
{
  "Subject": "AWS Health Alert: <service> - <category>",
  "Message": "Time: <time>\\nService: <service>\\nCategory: <category>\\n\\nDescription: <description>"
}
EOF
  }
}

# Allow EventBridge to publish to SNS
resource "aws_sns_topic_policy" "allow_eventbridge" {
  arn = aws_sns_topic.health_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "AllowEventBridgeToPublish"
    Statement = [
      {
        Sid       = "AllowEventBridgePublish"
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.health_alerts.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.health_events.arn
          }
        }
      }
    ]
  })
}