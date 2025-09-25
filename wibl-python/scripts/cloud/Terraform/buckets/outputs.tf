output "incoming_bucket_arn" {
    value = aws_s3_bucket.incoming_bucket.arn
}

output "incoming_bucket_id" {
    value = aws_s3_bucket.incoming_bucket.id
}
output "staging_bucket_arn"  {
    value = aws_s3_bucket.staging_bucket.arn
}

output "viz_bucket_arn" {
    value = aws_s3_bucket.viz_bucket.arn
}