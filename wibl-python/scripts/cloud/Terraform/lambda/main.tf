resource "aws_lambda_function" "conversion_lambda" {
    filename = "test_payload.zip"
    function_name = var.conversion_lambda_name
    role = aws_iam_role.conversion_lambda_role.arn
    handler = "wibl.processing.cloud.aws.lambda_function.lambda_handler"
    timeout = var.lambda_timeout
    runtime = var.python_version
    source_code_hash = filebase64sha256("./lambda/test_payload.zip")
    environment {
      variables = {
        "NOTIFICATION_ARN" = var.validation_topic_arn
        "PROVIDER_ID" = var.DCDB_PROVIDER_ID,
        "DEST_BUCKET" = var.staging_bucket_arn,
        "UPLOAD_POINT" = var.DCDB_UPLOAD_URL,
        "MANAGEMENT_URL" = var.MANAGEMENT_URL
      }
    }
    vpc_config {
      subnet_ids = [var.private_subnet]
      security_group_ids = [var.private_sg]
    }
}

resource "aws_lambda_permission" "allow_sns" {
  statement_id = "s3invoke"
  function_name = aws_lambda_function.conversion_lambda.function_name
  principal = "sns.amazonaws.com"
  source_arn = var.conversion_topic_arn
  action = "lambda:InvokeFunction"
}