data "aws_iam_policy_document" "lambda-trust-policy-doc" {
    statement {
        effect = "Allow"
        principals {
            type        = "Service"
            identifiers = ["lambda.amazonaws.com"]
        }
        actions = ["sts:AssumeRole"]
    }
}

data "aws_iam_policy_document" "lambda-nic-policy-doc" {
    statement {
        effect = "Allow"

        actions = ["ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeInstances",
        "ec2:AttachNetworkInterface"]

        resources = ["*"]
    }
}

data "aws_iam_policy_document" "lambda-s3-access-all-doc" {
    statement {
      sid = "LambdaAllowS3AccessAll"

      effect = "Allow"
      actions = ["s3:*"]
      resources = [var.incoming_bucket_arn, var.staging_bucket_arn]
    }
}

data "aws_iam_policy_document" "lambda-s3-access-staging-doc" {
    statement {
      sid = "LambdaAllowS3AccessStaging"

      effect = "Allow"
      actions = ["s3:*"]
      resources = [var.staging_bucket_arn]
    }
}

data "aws_iam_policy_document" "lambda-s3-access-incoming-doc" {
    statement {
      sid = "LambdaAllowS3AccessIncoming"

      effect = "Allow"
      actions = ["s3:*"]
      resources = [var.incoming_bucket_arn]
    }
}

data "aws_iam_policy_document" "lambda-sns-access-validation-doc" {
    statement {
      sid = "LambdaAllowSNSAccessValidation"
      effect = "Allow"
      actions = [ "sns:Publish" ]
      resources = [ var.validation_topic_arn ]
    }
}

data "aws_iam_policy_document" "lambda-sns-access-submission-doc" {
    statement {
      sid = "LambdaAllowSNSAccessSubmission"
      effect = "Allow"
      actions = [ "sns:Publish" ]
      resources = [ var.submission_topic_arn ]
    }
}

data "aws_iam_policy_document" "lambda-sns-access-submitted-doc" {
    statement {
      sid = "LambdaAllowSNSAccessSubmission"
      effect = "Allow"
      actions = [ "sns:Publish" ]
      resources = [ var.submitted_topic_arn ]
    }
}

data "aws_iam_policy_document" "lambda-sns-access-conversion-doc" {
    statement {
      sid = "LambdaAllowSNSAccessConversion"
      effect = "Allow"
      actions = [ "sns:Publish" ]
      resources = [ var.conversion_topic_arn ]
    }
}

resource "aws_iam_policy" "lambda-trust-policy" {
    name = "lambda-trust-policy"
    policy = data.aws_iam_policy_document.lambda-trust-policy-doc.json
}

resource "aws_iam_policy" "lambda-nic-policy" {
    name = "lambda-nic-policy"
    policy = data.aws_iam_policy_document.lambda-nic-policy-doc.json
}

resource "aws_iam_policy" "lambda-s3-access-all-policy" {
    name = "lambda-s3-access-all-policy"
    policy = data.aws_iam_policy_document.lambda-s3-access-all-doc.json
}

resource "aws_iam_policy" "lambda-s3-access-staging-policy" {
    name = "lambda-s3-access-staging-policy"
    policy = data.aws_iam_policy_document.lambda-s3-access-staging-doc.json
}

resource "aws_iam_policy" "lambda-s3-access-incoming-policy" {
    name = "lambda-s3-access-incoming-policy"
    policy = data.aws_iam_policy_document.lambda-s3-access-incoming-doc.json
}

resource "aws_iam_policy" "lamda-sns-access-validation" {
    name = "lambda-sns-access-validation"
    policy = data.aws_iam_policy_document.lambda-sns-access-validation-doc.json
}

resource "aws_iam_policy" "lamda-sns-access-submission" {
    name = "lambda-sns-access-submission"
    policy = data.aws_iam_policy_document.lambda-sns-access-submission-doc.json
}

resource "aws_iam_policy" "lamda-sns-access-submitted" {
    name = "lambda-sns-access-submitted"
    policy = data.aws_iam_policy_document.lambda-sns-access-submitted-doc.json
}

resource "aws_iam_policy" "lamda-sns-access-conversion" {
    name = "lambda-sns-access-conversion"
    policy = data.aws_iam_policy_document.lambda-sns-access-conversion-doc.json
}