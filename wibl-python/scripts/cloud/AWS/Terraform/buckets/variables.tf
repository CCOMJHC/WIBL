variable "incoming_bucket" {
    description = "Name of the incoming s3 bucket"
    type = string
}

variable "staging_bucket" {
    description = "Name of the staging s3 bucket"
    type = string
}

variable "viz_bucket" {
    description = "Name of the viz s3 bucket"
    type = string
}

variable "static_bucket" {
    description = "Name of the static bucket"
    type = string
}

variable "alb_url" {
    description = "Frontend cloudfront distribution url"
    type = string
}

variable "oai_iam_arn" {
    type = string
}