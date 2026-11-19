variable "kubeconfig_path" {
  description = "Path to the kubeconfig for the target cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace for the platform."
  type        = string
  default     = "netlab"
}

variable "api_image" {
  description = "API container image repository."
  type        = string
  default     = "ghcr.io/netlab-platform/api"
}

variable "web_image" {
  description = "Web container image repository."
  type        = string
  default     = "ghcr.io/netlab-platform/web"
}

variable "image_tag" {
  description = "Image tag for both services."
  type        = string
  default     = "latest"
}

variable "domain" {
  description = "Public hostname for the ingress. Empty disables the ingress."
  type        = string
  default     = ""
}

variable "ingress_class" {
  description = "Ingress class name."
  type        = string
  default     = "nginx"
}

variable "postgres_password" {
  description = "Postgres password. Pass via TF_VAR_postgres_password or a tfvars file — never commit it."
  type        = string
  sensitive   = true
}
