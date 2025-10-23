variable "tenancy_ocid" {
  description = "Tenancy OCID"
  type        = string
  validation {
    condition     = length(trimspace(var.tenancy_ocid)) > 0
    error_message = "Set tenancy_ocid (e.g. ocid1.tenancy.oc1...) via terraform.tfvars or ./setup.sh."
  }
}

variable "compartment_ocid" {
  description = "Compartment OCID for networking and compute resources"
  type        = string
  validation {
    condition     = length(trimspace(var.compartment_ocid)) > 0
    error_message = "Set compartment_ocid (target compartment for networking/compute)."
  }
}

variable "region" {
  description = "OCI region (e.g. eu-frankfurt-1)"
  type        = string
  validation {
    condition     = length(trimspace(var.region)) > 0
    error_message = "Set region (e.g. eu-frankfurt-1)."
  }
}

variable "availability_domain" {
  description = "Availability Domain name (leave empty to auto-select the first AD)"
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH public key for the opc user"
  type        = string
  validation {
    condition     = length(trimspace(var.ssh_public_key)) > 0
    error_message = "Provide the SSH public key contents for opc user access."
  }
}

variable "authorized_source_cidr" {
  description = "CIDR allowed to reach MCP ports (e.g., 203.0.113.10/32)."
  type        = string
  validation {
    condition     = length(trimspace(var.authorized_source_cidr)) > 0 && can(cidrhost(var.authorized_source_cidr, 0))
    error_message = "authorized_source_cidr must be a valid CIDR such as 203.0.113.10/32."
  }
}

variable "image_id" {
  description = "Optional custom OCI image OCID to use (skip auto-discovery)"
  type        = string
  default     = ""
}

variable "assign_public_ip" {
  description = "Whether to assign a public IP address to the instance"
  type        = bool
  default     = true
}

variable "instance_display_name" {
  description = "Display name for the compute instance"
  type        = string
  default     = "mcp-oci-streamable"
}

variable "shape" {
  description = "Compute shape (Flex shapes supported, e.g., VM.Standard.E4.Flex or VM.Standard.E3.Flex)"
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "ocpus" {
  description = "Number of OCPUs for Flex shape"
  type        = number
  default     = 2
}

variable "memory_in_gbs" {
  description = "Memory in GBs for Flex shape (must meet shape constraints)"
  type        = number
  default     = 32
}

variable "inject_user_data" {
  description = "Whether to include cloud-init user_data in metadata"
  type        = bool
  default     = true
}

variable "use_nsg" {
  description = "Attach the created NSG to the instance VNIC"
  type        = bool
  default     = true
}
