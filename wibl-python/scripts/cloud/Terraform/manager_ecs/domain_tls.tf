locals {
  domain = "${var.domain_host_name}.xyz"
}

resource "aws_route53domains_registered_domain" "main" {
  domain_name = local.domain

  admin_contact {
    first_name = "Admin"
    last_name  = "IT"
    contact_type = "PERSON"
    organization_name = "WIBL"
    address_line_1 = "123 Cloud St"
    city = "Columbus"
    state = "OH"
    country_code = "US"
    zip_code = "43004"
    phone_number = "+1.6145550100"
    email = "admin@${local.domain}"
  }
}


resource "aws_route53_zone" "internal" {
  name = local.domain
}

resource "aws_acm_certificate" "frontend" {
  domain_name       = local.domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "frontend_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.frontend.domain_validation_options :
    dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }

  zone_id = aws_route53_zone.internal.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "frontend" {
  certificate_arn         = aws_acm_certificate.frontend.arn
  validation_record_fqdns = [
    for record in aws_route53_record.frontend_cert_validation :
    record.fqdn
  ]
}