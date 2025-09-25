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