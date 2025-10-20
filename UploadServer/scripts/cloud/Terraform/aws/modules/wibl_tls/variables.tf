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

variable "server_cert_dns_names" {
  description = "DNS names for server certificate"
  type        = list(string)
  default     = ["localhost"]
}

variable "server_cert_ip_addrs" {
  description = "IP addresses for server certificate"
  type        = list(string)
  default     = ["127.0.0.1"]
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
