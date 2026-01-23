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

resource "aws_s3_bucket_public_access_block" "static_files" {
  bucket = aws_s3_bucket.static_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "static_files_public_read" {
  bucket = aws_s3_bucket.static_bucket.id
  depends_on = [aws_s3_bucket_public_access_block.static_files]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "arn:aws:s3:::gt-static-files-bucket/*"
      }
    ]
  })
}

resource "aws_s3_bucket_ownership_controls" "static_files" {
  bucket = aws_s3_bucket.static_bucket.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}
