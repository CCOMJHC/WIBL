resource "aws_lambda_function" "conversion_lambda" {
    filename = "test_payload.zip"
    function_name = var.conversion_lambda_name
    role = aws_iam_role.conversion_lambda_role.arn
    handler = "wibl.processing.cloud.aws.lambda_function.lambda_handler"
    timeout = var.lambda_timeout
    runtime = var.python_version
    memory_size = var.lambda_memory_size
    source_code_hash = filebase64sha256("./lambda/test_payload.zip")
    layers = [var.numpy_layer_name]
    architectures = [var.architecture]
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

resource "aws_lambda_permission" "conversion_allow_sns" {
  statement_id = "s3invoke"
  function_name = aws_lambda_function.conversion_lambda.function_name
  principal = "sns.amazonaws.com"
  source_arn = var.conversion_topic_arn
  action = "lambda:InvokeFunction"
}

resource "aws_lambda_function" "validation_lambda" {
  function_name = var.validation_lambda_name
  role = aws_iam_role.validation_lambda_role.arn
  handler = "wibl.validation.cloud.aws.lambda_function.lambda_handler"
  timeout = var.lambda_timeout
  runtime = var.python_version
  memory_size = var.lambda_memory_size
  source_code_hash = filebase64sha256("./lambda/test_payload.zip")
  layers = [var.numpy_layer_name]
  architectures = [var.architecture]
  environment {
    variables = {
      "NOTIFICATION_ARN" = var.submission_topic_arn
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

resource "aws_lambda_permission" "validation_allow_sns" {
  statement_id = "s3invoke"
  function_name = aws_lambda_function.validation_lambda.function_name
  principal = "sns.amazonaws.com"
  source_arn = var.validation_topic_arn
  action = "lambda:InvokeFunction"
}

resource "aws_lambda_function" "submission_lambda" {
  function_name = var.submission_lambda_name
  role = aws_iam_role.submission_lambda_role.arn
  handler = "wibl.submission.cloud.aws.lambda_function.lambda_handler"
  timeout = var.lambda_timeout
  runtime = var.python_version
  memory_size = var.lambda_memory_size
  source_code_hash = filebase64sha256("./lambda/test_payload.zip")
  layers = [var.numpy_layer_name]
  architectures = [var.architecture]
  environment {
    variables = {
      "NOTIFICATION_ARN" = var.submitted_topic_arn
      "PROVIDER_ID" = var.DCDB_PROVIDER_ID,
      "PROVIDER_AUTH" = var.provider_auth,
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

resource "aws_lambda_permission" "submission_allow_sns" {
  statement_id = "s3invoke"
  function_name = aws_lambda_function.submission_lambda.function_name
  principal = "sns.amazonaws.com"
  source_arn = var.submission_topic_arn
  action = "lambda:InvokeFunction"
}

resource "aws_lambda_function" "conversion_start_lambda" {
  function_name = var.conversion_start_lambda_name
  role = aws_iam_role.conversion_start_lambda_role.arn
  handler = "wibl.upload.cloud.aws.lambda_function.lambda_handler"
  timeout = var.lambda_timeout
  runtime = var.python_version
  memory_size = var.lambda_memory_size
  source_code_hash = filebase64sha256("./lambda/test_payload.zip")
  layers = [var.numpy_layer_name]
  architectures = [var.architecture]
  environment {
    variables = {
      "NOTIFICATION_ARN" = var.conversion_topic_arn
      "PROVIDER_ID" = var.DCDB_PROVIDER_ID,
      "PROVIDER_AUTH" = var.provider_auth,
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

resource "aws_lambda_permission" "submission_allow_url_access" {
  statement_id = "url"
  function_name = aws_lambda_function.conversion_start_lambda.function_name
  principal = "*"
  function_url_auth_type = "NONE"
  action = "lambda:InvokeFunctionUrl"
}

resource "aws_lambda_function_url" "conversion_start_lambda_url" {
  function_name = var.conversion_start_lambda_name
  authorization_type = "NONE"
}



