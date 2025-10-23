locals {
  tcp_ports = [
    7001, 7002, 7003, 7004, 7005, 7006, 7007, 7008, 7009, 7010, 7011,
    8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010, 8011
  ]

  selected_image_id = length(trimspace(var.image_id)) > 0 ? var.image_id : (
    length(data.oci_core_images.oracle_linux.images) > 0 ? data.oci_core_images.oracle_linux.images[0].id : (
      length(data.oci_core_images.oracle_linux_anyshape.images) > 0 ? data.oci_core_images.oracle_linux_anyshape.images[0].id : ""
    )
  )
  authorized_source = var.authorized_source_cidr

  metadata_base = {
    ssh_authorized_keys = var.ssh_public_key
  }
  metadata_full = var.inject_user_data ? merge(local.metadata_base, {
    user_data = base64encode(templatefile("${path.module}/templates/cloud-init.tpl", { authorized_source = local.authorized_source }))
  }) : local.metadata_base
}

data "oci_core_images" "oracle_linux" {
  compartment_id   = var.tenancy_ocid
  operating_system = "Oracle Linux"
  shape            = var.shape
  sort_by          = "TIMECREATED"
  sort_order       = "DESC"
}

data "oci_core_images" "oracle_linux_anyshape" {
  compartment_id   = var.tenancy_ocid
  operating_system = "Oracle Linux"
  sort_by          = "TIMECREATED"
  sort_order       = "DESC"
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

resource "oci_core_vcn" "mcp" {
  compartment_id = var.compartment_ocid
  cidr_block     = "10.42.0.0/16"
  display_name   = "mcp-oci-vcn"
  dns_label      = "mcpoci"
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_ocid
  display_name   = "mcp-oci-igw"
  vcn_id         = oci_core_vcn.mcp.id
  enabled        = true
}

resource "oci_core_route_table" "rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.mcp.id
  display_name   = "mcp-oci-rt"

  route_rules {
    network_entity_id = oci_core_internet_gateway.igw.id
    destination       = "0.0.0.0/0"
    description       = "Default route to internet"
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.mcp.id
  cidr_block                 = "10.42.1.0/24"
  display_name               = "mcp-oci-public-subnet"
  dns_label                  = "mcpsubnet"
  route_table_id             = oci_core_route_table.rt.id
  prohibit_public_ip_on_vnic = false
}

resource "oci_core_network_security_group" "mcp" {
  compartment_id = var.compartment_ocid
  display_name   = "mcp-oci-nsg"
  vcn_id         = oci_core_vcn.mcp.id
}

resource "oci_core_network_security_group_security_rule" "egress_all" {
  network_security_group_id = oci_core_network_security_group.mcp.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  description               = "Allow all outbound traffic"
}

resource "oci_core_network_security_group_security_rule" "ingress_ports" {
  for_each = { for port in local.tcp_ports : tostring(port) => port }

  network_security_group_id = oci_core_network_security_group.mcp.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = local.authorized_source
  description               = "Allow TCP port ${each.value}"

  tcp_options {
    destination_port_range {
      min = each.value
      max = each.value
    }
  }
}

resource "oci_core_instance" "mcp_vm" {
  count = length(local.selected_image_id) > 0 ? 1 : 0

  depends_on = [
    oci_core_network_security_group_security_rule.egress_all,
    oci_core_network_security_group_security_rule.ingress_ports,
  ]

  compartment_id      = var.compartment_ocid
  availability_domain = length(trimspace(var.availability_domain)) > 0 ? var.availability_domain : data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = var.instance_display_name

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = var.assign_public_ip
    nsg_ids          = var.use_nsg ? [oci_core_network_security_group.mcp.id] : []
  }

  shape = var.shape

  dynamic "shape_config" {
    for_each = can(regex("Flex", var.shape)) ? [1] : []
    content {
      ocpus         = var.ocpus
      memory_in_gbs = var.memory_in_gbs
    }
  }

  source_details {
    source_type             = "image"
    source_id               = local.selected_image_id
    boot_volume_size_in_gbs = 100
  }

  metadata = local.metadata_full
}

resource "null_resource" "image_unavailable" {
  count = length(local.selected_image_id) > 0 ? 0 : 1

  provisioner "local-exec" {
    command     = "echo 'No Oracle Linux platform image matched the current filters. Rerun ./setup.sh to save an explicit image_id or pass -var \"image_id=...\".' >&2; exit 1"
    interpreter = ["/bin/bash", "-c"]
  }
}
