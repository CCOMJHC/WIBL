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

data "aws_iam_policy_document" "lambda-sns-access-validation-doc" {
    statement {
      sid = "LambdaAllowSNSAccessValidation"
      effect = "Allow"
      actions = [ "sns:Publish" ]
      resources = [ var.validation_topic_arn ]
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

resource "aws_iam_policy" "lamda-sns-access-validation" {
    name = "lambda-sns-access-validation"
    policy = data.aws_iam_policy_document.lambda-sns-access-validation-doc.json
}