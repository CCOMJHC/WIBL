data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
# TODO: Why is it saying that "bucket_namespace" is not expected here?
resource "aws_s3_bucket" "incoming_bucket" {
    bucket = format("%s-%s-%s-an", var.incoming_bucket, data.aws_caller_identity.current.account_id, data.aws_region.current.region)
    force_destroy = true
    bucket_namespace = "account-regional"
}

resource "aws_s3_bucket" "staging_bucket" {
    bucket = format("%s-%s-%s-an", var.staging_bucket, data.aws_caller_identity.current.account_id, data.aws_region.current.region)
    force_destroy = true
    bucket_namespace = "account-regional"
}

resource "aws_s3_bucket" "viz_bucket" {
    bucket = format("%s-%s-%s-an", var.viz_bucket, data.aws_caller_identity.current.account_id, data.aws_region.current.region)
    force_destroy = true
    bucket_namespace = "account-regional"
}

resource "aws_s3_bucket" "static_bucket" {
    bucket = format("%s-%s-%s-an", var.static_bucket, data.aws_caller_identity.current.account_id, data.aws_region.current.region)
    force_destroy = true
    bucket_namespace = "account-regional"
}

data "aws_iam_policy_document" "static_bucket_policy" {
  statement {
    actions = ["s3:GetObject"]

    resources = [
      "${aws_s3_bucket.static_bucket.arn}/static/*"
    ]

    principals {
      type        = "AWS"
      identifiers = [var.oai_iam_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "static" {
  bucket = aws_s3_bucket.static_bucket.id
  policy = data.aws_iam_policy_document.static_bucket_policy.json
}

resource "aws_s3_bucket_cors_configuration" "static_files" {
  bucket = aws_s3_bucket.static_bucket.id

  cors_rule {
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [var.alb_url]
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
  depends_on = [aws_s3_bucket.static_bucket]
}

