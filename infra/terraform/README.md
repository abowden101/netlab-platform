# Hosted deployment (Terraform + Helm)

Installs the chart from `infra/helm` into a Kubernetes cluster. The API
needs a lab host with Docker + Containerlab — in this skeleton the API pod
mounts the node's Docker socket (see the Helm values). For a real hosted
deployment, run the API on a dedicated lab host and restrict API access.

```bash
cd infra/terraform
terraform init
terraform apply \
  -var postgres_password="$POSTGRES_PASSWORD" \
  -var domain="netlab.example.com"
```

Variables: see `variables.tf`. Never commit a `*.tfvars` file containing
the Postgres password.
