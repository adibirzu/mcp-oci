output "vcn_id" {
  description = "Created VCN OCID"
  value       = oci_core_vcn.mcp.id
}

output "subnet_id" {
  description = "Public subnet OCID"
  value       = oci_core_subnet.public.id
}

output "network_security_group_id" {
  description = "Network Security Group OCID"
  value       = oci_core_network_security_group.mcp.id
}

output "instance_id" {
  description = "Compute instance OCID"
  value       = length(oci_core_instance.mcp_vm) > 0 ? oci_core_instance.mcp_vm[0].id : null
}

output "instance_public_ip" {
  description = "Public IP address (if assigned)"
  value       = length(oci_core_instance.mcp_vm) > 0 ? try(oci_core_instance.mcp_vm[0].public_ip, null) : null
}

output "selected_image_id" {
  description = "Image OCID used for the instance"
  value       = local.selected_image_id
}

output "resolved_ad" {
  description = "Availability Domain used"
  value       = length(trimspace(var.availability_domain)) > 0 ? var.availability_domain : data.oci_identity_availability_domains.ads.availability_domains[0].name
}

output "shape_debug" {
  description = "Shape and resources"
  value       = {
    shape  = var.shape
    ocpus  = var.ocpus
    memory = var.memory_in_gbs
  }
}
