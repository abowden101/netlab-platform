terraform {
  required_version = ">= 1.5"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

resource "kubernetes_namespace" "netlab" {
  metadata {
    name = var.namespace
  }
}

resource "helm_release" "netlab" {
  name       = "netlab"
  namespace  = kubernetes_namespace.netlab.metadata[0].name
  chart      = "../helm"
  version    = "0.1.0"
  values = [
    yamlencode({
      image = {
        api = { repository = var.api_image, tag = var.image_tag }
        web = { repository = var.web_image, tag = var.image_tag }
      }
      ingress = {
        enabled   = var.domain != ""
        host      = var.domain
        className = var.ingress_class
      }
      postgres = { password = var.postgres_password }
    }),
  ]
}
