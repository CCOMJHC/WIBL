output "architecture" {
  value = var.architecture
}

output "python_version" {
  value = var.python_version
}

output "conversion_lambda_name" {
  value = var.conversion_lambda_name
}

output "conversion_start_lambda_name" {
  value = var.conversion_start_lambda_name
}

output "validation_lambda_name" {
  value = var.validation_lambda_name
}

output "submission_lambda_name" {
  value = var.submission_lambda_name
}

output "frontend_hostname" {
  value = module.configure-manager-ecs.frontend_hostname
}

output "wibl_aws_region" {
  value = var.region
}

output "incoming_bucket_name" {
  value = module.configure-buckets.incoming_bucket_full_name
}
