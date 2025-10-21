variable "tenancy_ocid" {
  description = "Tenancy OCID"
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment OCID"
  type        = string
}

variable "region" {
  description = "OCI Region"
  type        = string
}

variable "cluster_name" {
  description = "OKE Cluster Name"
  type        = string
  default     = "mcp-oke-cluster"
}

variable "dynamic_group_name" {
  description = "Dynamic Group Name"
  type        = string
  default     = "MCP-Dynamic"
}

variable "namespace" {
  description = "Kubernetes Namespace"
  type        = string
  default     = "default"
}

variable "vcn_id" {
  description = "VCN OCID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet OCID"
  type        = string
}

variable "availability_domain" {
  description = "Availability Domain"
  type        = string
}

variable "image_id" {
  description = "Node pool image ID"
  type        = string
  default     = "ocid1.image.oc1.iad.aaaaaaaaxxxxxxxxxx"  # Replace with actual
}

variable "kms_key_id" {
  description = "KMS Key ID for encryption (optional)"
  type        = string
  default     = ""
}
