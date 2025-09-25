resource "aws_iam_role" "conversion_lambda_role" {
  name = var.conversion_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda-trust-policy-doc.json
}

resource "aws_iam_role" "validation_lambda_role" {
  name = var.validation_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda-trust-policy-doc.json
}

resource "aws_iam_role" "submission_lambda_role" {
  name = var.submission_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda-trust-policy-doc.json
}

resource "aws_iam_role" "conversion_start_lambda_role" {
  name = var.conversion_start_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda-trust-policy-doc.json
}

resource "aws_iam_role" "viz_lambda_role" {
  name = var.viz_lambda_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda-trust-policy-doc.json
}

resource "aws_iam_policy_attachment" "lambda_basic_policy_attach" {
  name       = "lambda_basic_policy_attach"

  roles      = [aws_iam_role.conversion_lambda_role.name, aws_iam_role.submission_lambda_role.name,
  aws_iam_role.validation_lambda_role.name, aws_iam_role.viz_lambda_role.name, aws_iam_role.conversion_start_lambda_role.name]

  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

}

resource "aws_iam_policy_attachment" "lambda_nic_policy_attach" {
  name       = "lambda_nic_policy_attach"

  roles      = [aws_iam_role.conversion_lambda_role.name, aws_iam_role.submission_lambda_role.name,
  aws_iam_role.validation_lambda_role.name, aws_iam_role.viz_lambda_role.name, aws_iam_role.conversion_start_lambda_role.name]

  policy_arn = aws_iam_policy.lambda-nic-policy.arn
}

resource "aws_iam_policy_attachment" "conversion_lambda_s3_access_policy_attach" {
  name       = "lambda_s3_access_policy_attach"

  roles      = [aws_iam_role.conversion_lambda_role.name]

  policy_arn = aws_iam_policy.lambda-s3-access-all-policy.arn
}

resource "aws_iam_policy_attachment" "conversion_lambda_sns_validation_policy_attach" {
    name = "lambda_sns_validation_policy_attach"
    roles = [aws_iam_role.conversion_lambda_role.name]
    policy_arn = aws_iam_policy.lambda-sns-access-validation.arn
}

resource "aws_iam_policy_attachment" "validation_lambda_s3_access_policy_attach" {
  name       = "validation_lambda_s3_access_policy_attach"
  roles = [aws_iam_role.validation_lambda_role.name]
  policy_arn = aws_iam_policy.lambda-s3-access-staging-policy.arn
}

resource "aws_iam_policy_attachment" "validation_lambda_sns_submission_policy_attach" {
    name = "validation_lambda_sns_submission_policy_attach"
    roles = [aws_iam_role.validation_lambda_role.name]
    policy_arn = aws_iam_policy.lambda-sns-access-submission.arn
}

resource "aws_iam_policy_attachment" "submission_lambda_s3_access_policy_attach" {
  name       = "submission_lambda_s3_access_policy_attach"
  roles = [aws_iam_role.submission_lambda_role.name]
  policy_arn = aws_iam_policy.lambda-s3-access-staging-policy.arn
}

resource "aws_iam_policy_attachment" "submission_lambda_sns_submitted_policy_attach" {
    name = "submission_lambda_sns_submitted_policy_attach"
    roles = [aws_iam_role.submission_lambda_role.name]
    policy_arn = aws_iam_policy.lambda-sns-access-submitted.arn
}

resource "aws_iam_policy_attachment" "conversion_start_lambda_s3_access_policy_attach" {
  name       = "conversion_start_lambda_s3_access_policy_attach"
  roles = [aws_iam_role.conversion_start_lambda_role.name]
  policy_arn = aws_iam_policy.lambda-s3-access-incoming-policy.arn
}

resource "aws_iam_policy_attachment" "conversion_start_lambda_sns_conversion_policy_attach" {
    name = "conversion_start_lambda_sns_conversion_policy_attach"
    roles = [aws_iam_role.conversion_start_lambda_role.name]
    policy_arn = aws_iam_policy.lambda-sns-access-conversion.arn
}
