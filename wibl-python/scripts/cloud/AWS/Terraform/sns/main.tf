resource "aws_sns_topic" "conversion_topic" {
    name = var.conversion_topic_name
}

resource "aws_sns_topic" "validation_topic" {
    name = var.validation_topic_name
}

resource "aws_sns_topic" "submission_topic" {
    name = var.submission_topic_name
}

resource "aws_sns_topic" "submitted_topic" {
    name = var.submitted_topic_name
}