terraform {
  required_providers {
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

# Variables for certificate subjects
variable "out_dir" {
  description = "Output directory for certificates"
  type        = string
  default     = "certs"
}

variable "ca_common_name" {
  description = "Common name for CA certificate"
  type        = string
  default     = "localhost"
}

variable "server_common_name" {
  description = "Common name for server certificate"
  type        = string
  default     = "localhost"
}

variable "client_hostname" {
  description = "Hostname for client certificate"
  type        = string
  default     = "wibl-logger"
}

variable "country" {
  description = "Country code for certificate subjects"
  type        = string
  default     = "US"
}

variable "state" {
  description = "State for certificate subjects"
  type        = string
  default     = "NewHampshire"
}

variable "locality" {
  description = "Locality for certificate subjects"
  type        = string
  default     = "Durham"
}

variable "organization" {
  description = "Organization for certificate subjects"
  type        = string
  default     = "CCOM-JHC"
}

# CA Certificate (Self-signed)
resource "tls_private_key" "ca" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "ca" {
  private_key_pem = tls_private_key.ca.private_key_pem

  subject {
    country             = var.country
    province            = var.state
    locality            = var.locality
    organization        = var.organization
    organizational_unit = "CA"
    common_name         = var.ca_common_name
  }

  validity_period_hours = 87600 # 10-years

  allowed_uses = [
    "cert_signing",
    "key_encipherment",
    "digital_signature",
  ]

  dns_names    = ["localhost"]
  ip_addresses = ["127.0.0.1"]

  is_ca_certificate = true
}

# Server Certificate
resource "tls_private_key" "server" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_cert_request" "server" {
  private_key_pem = tls_private_key.server.private_key_pem

  subject {
    country             = var.country
    province            = var.state
    locality            = var.locality
    organization        = var.organization
    organizational_unit = "Server"
    common_name         = var.server_common_name
  }

  dns_names    = ["localhost"]
  ip_addresses = ["127.0.0.1"]
}

resource "tls_locally_signed_cert" "server" {
  cert_request_pem   = tls_cert_request.server.cert_request_pem
  ca_private_key_pem = tls_private_key.ca.private_key_pem
  ca_cert_pem        = tls_self_signed_cert.ca.cert_pem

  validity_period_hours = 8760 # 365 days

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

# Client Certificate
resource "tls_private_key" "client" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_cert_request" "client" {
  private_key_pem = tls_private_key.client.private_key_pem

  subject {
    country             = var.country
    province            = var.state
    locality            = var.locality
    organization        = var.organization
    organizational_unit = "Client"
    common_name         = var.client_hostname
  }

  dns_names    = ["localhost"]
  ip_addresses = ["127.0.0.1"]
}

resource "tls_locally_signed_cert" "client" {
  cert_request_pem   = tls_cert_request.client.cert_request_pem
  ca_private_key_pem = tls_private_key.ca.private_key_pem
  ca_cert_pem        = tls_self_signed_cert.ca.cert_pem

  validity_period_hours = 8760 # 365 days

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "client_auth",
  ]
}

# Write certificates and keys to files
resource "local_file" "ca_key" {
  content         = tls_private_key.ca.private_key_pem
  filename        = "${var.out_dir}/ca.key"
  file_permission = "0600"
}

resource "local_file" "ca_crt" {
  content         = tls_self_signed_cert.ca.cert_pem
  filename        = "${var.out_dir}/ca.crt"
  file_permission = "0644"
}

resource "local_file" "server_key" {
  content         = tls_private_key.server.private_key_pem
  filename        = "${var.out_dir}/server.key"
  file_permission = "0600"
}

resource "local_file" "server_csr" {
  content         = tls_cert_request.server.cert_request_pem
  filename        = "${var.out_dir}/server.csr"
  file_permission = "0644"
}

resource "local_file" "server_crt" {
  content         = tls_locally_signed_cert.server.cert_pem
  filename        = "${var.out_dir}/server.crt"
  file_permission = "0644"
}

resource "local_file" "client_key" {
  content         = tls_private_key.client.private_key_pem
  filename        = "${var.out_dir}/client.key"
  file_permission = "0600"
}

resource "local_file" "client_csr" {
  content         = tls_cert_request.client.cert_request_pem
  filename        = "${var.out_dir}/client.csr"
  file_permission = "0644"
}

resource "local_file" "client_crt" {
  content         = tls_locally_signed_cert.client.cert_pem
  filename        = "${var.out_dir}/client.crt"
  file_permission = "0644"
}

# Outputs for easy access to certificate details
output "certificate_directory" {
  description = "Directory where certificates were written"
  value       = var.out_dir
}
