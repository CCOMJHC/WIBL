resource "aws_iam_role" "conversion_lambda_role" {
  name = var.conversion_lambda_role_name
  assume_role_policy = aws_iam_policy.lambda-trust-policy.arn
}

resource "aws_iam_role" "validation_lambda_role" {
  name = var.validation_lambda_role_name
  assume_role_policy = aws_iam_policy.lambda-trust-policy.arn
}

resource "aws_iam_role" "submission_lambda_role" {
  name = var.submission_lambda_role_name
  assume_role_policy = aws_iam_policy.lambda-trust-policy.arn
}

resource "aws_iam_role" "conversion_start_lambda_role" {
  name = var.conversion_start_lambda_role_name
  assume_role_policy = aws_iam_policy.lambda-trust-policy.arn
}

resource "aws_iam_role" "viz_lambda_role" {
  name = var.viz_lambda_role_name
  assume_role_policy = aws_iam_policy.lambda-trust-policy.arn
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

resource "aws_iam_policy_attachment" "lambda_s3_access_policy_attach" {
  name       = "lambda_s3_access_policy_attach"

  roles      = [aws_iam_role.conversion_lambda_role.name]

  policy_arn = aws_iam_policy.lambda-s3-access-all-policy.arn
}

resource "aws_iam_policy_attachment" "lambda_sns_validation_policy_attach" {
    name = "lambda_sns_validation_policy_attach"
    roles = [aws_iam_role.conversion_lambda_role.name]
    policy_arn = aws_iam_policy.lamda-sns-access-validation.arn
}