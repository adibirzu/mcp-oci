terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.29.0"
    }
  }
}

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

variable "cluster_id" {
  description = "OKE Cluster ID (existing)"
  type        = string
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
}

provider "oci" {
  tenancy_ocid = var.tenancy_ocid
  region       = var.region
}

data "oci_containerengine_cluster" "existing_cluster" {
  cluster_id = var.cluster_id
}

resource "oci_containerengine_node_pool" "mcp_nodepool" {
  cluster_id     = var.cluster_id
  compartment_id = var.compartment_ocid
  name           = "mcp-nodepool"

  node_shape = "VM.Standard.E4.Flex"

  node_source {
    image_id = var.image_id
  }

  node_pool_placement_configs {
    availability_domain = var.availability_domain
    subnet_id           = var.subnet_id
  }

  node_config_details {
    size = 1
    block_volume_size_in_gbs = 50
  }

  quantity_per_subnet = 1
  kubernetes_version  = data.oci_containerengine_cluster.existing_cluster.kubernetes_version
}

resource "oci_identity_dynamic_group" "mcp_dynamic" {
  compartment_id = var.compartment_ocid
  name           = var.dynamic_group_name
  description    = "Dynamic group for MCP OCI servers"
  matching_rule  = "ALL {request.principal.type = 'cluster', request.principal.compartment.id = '${var.compartment_ocid}'} WHERE target.cluster.id = '${var.cluster_id}'"
}

resource "oci_identity_policy" "mcp_compute_policy" {
  compartment_id = var.compartment_ocid
  description    = "MCP servers access to compute, DB, network"
  name           = "MCP-Policy-Compute-DB-Network"
  statements = [
    "Allow dynamic-group ${var.dynamic_group_name} to manage compute-family in tenancy",
    "Allow dynamic-group ${var.dynamic_group_name} to manage database-family in tenancy",
    "Allow dynamic-group ${var.dynamic_group_name} to manage network-family in tenancy",
    "Allow dynamic-group ${var.dynamic_group_name} to manage load-balancer-family in tenancy"
  ]
}

resource "oci_identity_policy" "mcp_observability_policy" {
  compartment_id = var.compartment_ocid
  description    = "MCP servers access to observability services"
  name           = "MCP-Policy-Observability"
  statements = [
    "Allow dynamic-group ${var.dynamic_group_name} to manage logging-family in tenancy",
    "Allow dynamic-group ${var.dynamic_group_name} to manage monitoring-family in tenancy"
  ]
}

resource "oci_identity_policy" "mcp_cost_policy" {
  compartment_id = var.compartment_ocid
  description    = "MCP servers access to cost services"
  name           = "MCP-Policy-Cost"
  statements = [
    "Allow dynamic-group ${var.dynamic_group_name} to use usage-api in tenancy",
    "Allow dynamic-group ${var.dynamic_group_name} to manage budgets in tenancy"
  ]
}

# Kubernetes provider - assumes kubeconfig set
provider "kubernetes" {
  config_path = pathexpand("~/.kube/config")
}

resource "kubernetes_secret" "mcp_config" {
  metadata {
    name      = "mcp-config"
    namespace = var.namespace
  }

  data = {
    compartment-ocid = var.compartment_ocid
    region           = var.region
  }
}

resource "kubernetes_deployment" "mcp_servers" {
  metadata {
    name      = "mcp-oci-servers"
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "mcp-oci-servers"
      }
    }

    template {
      metadata {
        labels = {
          app = "mcp-oci-servers"
        }
      }

      spec {
        service_account_name = "mcp-service-account"

        container {
          image = "your-ocir-repo/mcp-oci:latest"
          name  = "mcp-servers"

          port {
            container_port = 8000
          }

          port {
            container_port = 8001
          }

          port {
            container_port = 8002
          }

          port {
            container_port = 8003
          }

          port {
            container_port = 8004
          }

          port {
            container_port = 8005
          }

          port {
            container_port = 8006
          }

          port {
            container_port = 8007
          }

          port {
            container_port = 8008
          }

          port {
            container_port = 8009
          }

          port {
            container_port = 8010
          }

          env {
            name  = "OCI_CLI_AUTH"
            value = "instance_principal"
          }

          env {
            name = "COMPARTMENT_OCID"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.mcp_config.metadata[0].name
                key  = "compartment-ocid"
              }
            }
          }

          env {
            name = "OCI_REGION"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.mcp_config.metadata[0].name
                key  = "region"
              }
            }
          }

          resources {
            requests = {
              cpu    = "500m"
              memory = "1Gi"
            }
            limits = {
              cpu    = "1"
              memory = "2G"
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "mcp_service" {
  metadata {
    name      = "mcp-oci-service"
    namespace = var.namespace
  }

  spec {
    type = "LoadBalancer"

    port {
      name        = "mcp-port-8000"
      port        = 8000
      target_port = 8000
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8001"
      port        = 8001
      target_port = 8001
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8002"
      port        = 8002
      target_port = 8002
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8003"
      port        = 8003
      target_port = 8003
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8004"
      port        = 8004
      target_port = 8004
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8005"
      port        = 8005
      target_port = 8005
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8006"
      port        = 8006
      target_port = 8006
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8007"
      port        = 8007
      target_port = 8007
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8008"
      port        = 8008
      target_port = 8008
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8009"
      port        = 8009
      target_port = 8009
      protocol    = "TCP"
    }

    port {
      name        = "mcp-port-8010"
      port        = 8010
      target_port = 8010
      protocol    = "TCP"
    }

    selector = {
      app = "mcp-oci-servers"
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler" "mcp_hpa" {
  metadata {
    name      = "mcp-oci-hpa"
    namespace = var.namespace
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment.mcp_servers.metadata[0].name
    }

    min_replicas = 1
    max_replicas = 5

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 50
        }
      }
    }

    metric {
      type = "Resource"
      resource {
        name = "memory"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}
