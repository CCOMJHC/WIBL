resource "aws_s3_bucket" "incoming_bucket" {
    bucket = var.incoming_bucket
    force_destroy = true
}

resource "aws_s3_bucket" "staging_bucket" {
    bucket = var.staging_bucket
    force_destroy = true
}

resource "aws_s3_bucket" "viz_bucket" {
    bucket = var.viz_bucket
    force_destroy = true
}

resource "aws_s3_bucket" "static_bucket" {
    bucket = var.static_bucket
    force_destroy = true
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

