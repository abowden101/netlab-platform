output "namespace" {
  description = "Namespace the platform was installed into."
  value       = kubernetes_namespace.netlab.metadata[0].name
}

output "domain" {
  description = "Public hostname, if an ingress was enabled."
  value       = var.domain
}
