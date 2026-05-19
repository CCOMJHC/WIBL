output "conversion_topic_arn" {
    value = aws_sns_topic.conversion_topic.arn
}

output "validation_topic_arn" {
    value = aws_sns_topic.validation_topic.arn
}

output "submission_topic_arn" {
    value = aws_sns_topic.submission_topic.arn
}

output "submitted_topic_arn" {
    value = aws_sns_topic.submitted_topic.arn
}