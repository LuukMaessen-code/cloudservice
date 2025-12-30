# Cloudservice Demo — NATS + React Chat

Minimal event-driven chat demo inspired by `dverse-platform-archictecture`. Components:
- **Gateway**: FastAPI WebSocket bridge that publishes chat messages to NATS JetStream and fans out live updates to connected clients.
- **History service**: FastAPI + JetStream consumer that appends chat messages to JSONL files and serves message history.
- **Frontend**: Vite/React UI for joining rooms and chatting.
- **Infra**: Docker Compose for local dev and Kubernetes manifests for cloud runs.

## Quickstart (local dev)
```bash
# 1) start stack
docker compose up --build

# 2) open UI
http://localhost:5173
```

## Services & Ports
- Gateway API/WebSocket: `http://localhost:8000`
- History API: `http://localhost:9000`
- Frontend: `http://localhost:5173`
- NATS: `nats://localhost:4222` (JetStream enabled), monitoring `:8222`

## Kubernetes (cloud only)
Kubernetes manifests are provided for cloud deployment. For local development, use Docker Compose and localhost endpoints. Ingress is not required for local development.
docker build -t cloudservice-frontend:local -f frontend/web/Dockerfile frontend/web
```

With the Makefile you can build/push with custom registry/tag:
```bash
# defaults: REGISTRY=local TAG=latest
make build-images REGISTRY=ghcr.io/your-org TAG=v1
make push-images  REGISTRY=ghcr.io/your-org TAG=v1
```

## Terraform (EKS)
An opinionated Terraform stack lives in `infra/terraform` using the official VPC and EKS modules.

Prereqs: Terraform >=1.6, AWS credentials exported (e.g., `AWS_PROFILE` or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars  # adjust values as needed

terraform init
terraform plan
terraform apply

# Configure kubectl for the new cluster
aws eks update-kubeconfig --name <cluster_name> --region <aws_region>

# Then apply the app manifests
kubectl apply -f ../k8s/namespace.yaml
kubectl apply -f ../k8s/nats.yaml
kubectl apply -f ../k8s/gateway.yaml
kubectl apply -f ../k8s/history.yaml
kubectl apply -f ../k8s/frontend.yaml
```

## Make targets
- `make dev` — run full Docker Compose stack
- `make down` — stop the stack
- `make logs` — follow container logs
- `make build-images` / `make push-images` — build/push gateway, history, frontend images (`REGISTRY`, `TAG` overridable)
- `make k8s-apply` / `make k8s-delete` — apply or remove K8s manifests (uses current kube context)
- `make tf-init|tf-plan|tf-apply|tf-destroy` — Terraform helpers for EKS

## Project Layout
- `services/gateway` — WebSocket bridge
- `services/history_service` — JSONL history + REST
- `frontend/web` — React client (Vite)
- `infra/docker` — docker-compose for local dev
- `infra/k8s` — minimal K8s manifests

## Notes
- History is stored locally as newline-delimited JSON files under `/data/history/room_<id>.jsonl`. Mount a volume in Docker/K8s to persist.
- JetStream stream `CHAT` is auto-provisioned (subjects `chat.room.*`).

