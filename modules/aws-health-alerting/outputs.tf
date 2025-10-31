output "sns_topic_arn" {
  description = "ARN of the SNS topic receiving AWS Health alerts"
  value       = aws_sns_topic.health_alerts.arn
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule capturing AWS Health events"
  value       = aws_cloudwatch_event_rule.health_events.arn
}

output "email_subscription_status" {
  description = "Status of the email subscription (PendingConfirmation until confirmed)"
  value       = aws_sns_topic_subscription.email.subscription_arn
}