PROJECT := cloudservice-demo
COMPOSE := infra/docker/docker-compose.dev.yaml
REGISTRY ?= luukmn
TAG ?= latest

IMG_GATEWAY := $(REGISTRY)/cloudservice-gateway:$(TAG)
IMG_HISTORY := $(REGISTRY)/cloudservice-history:$(TAG)
IMG_FRONTEND := $(REGISTRY)/cloudservice-frontend:$(TAG)

.PHONY: dev down logs k8s-apply k8s-delete tf-init tf-plan tf-apply tf-destroy build-images push-images

# Run full stack locally (NATS + gateway + history + frontend)
dev:
	docker compose -f $(COMPOSE) up --build

down:
	docker compose -f $(COMPOSE) down

logs:
	docker compose -f $(COMPOSE) logs -f

# Build & push container images
build-images:
	docker build -t $(IMG_GATEWAY) -f services/gateway/Dockerfile .
	docker build -t $(IMG_HISTORY) -f services/history_service/Dockerfile .
	docker build -t $(IMG_FRONTEND) -f frontend/web/Dockerfile frontend/web

push-images: build-images
	docker push $(IMG_GATEWAY)
	docker push $(IMG_HISTORY)
	docker push $(IMG_FRONTEND)

# Apply/delete Kubernetes manifests
k8s-apply:
	kubectl apply -f infra/k8s/namespace.yaml
	kubectl apply -f infra/k8s/nats.yaml
	kubectl apply -f infra/k8s/gateway.yaml
	kubectl apply -f infra/k8s/history.yaml
	kubectl apply -f infra/k8s/history-pvc.yaml
	kubectl apply -f infra/k8s/frontend.yaml
	kubectl apply -f infra/k8s/ingress.yaml

k8s-delete:
	kubectl delete -f infra/k8s/frontend.yaml --ignore-not-found
	kubectl delete -f infra/k8s/history.yaml --ignore-not-found
	kubectl delete -f infra/k8s/history-pvc.yaml --ignore-not-found
	kubectl delete -f infra/k8s/gateway.yaml --ignore-not-found
	kubectl delete -f infra/k8s/nats.yaml --ignore-not-found
	kubectl delete -f infra/k8s/ingress.yaml --ignore-not-found
	kubectl delete -f infra/k8s/namespace.yaml --ignore-not-found

# Terraform helpers (run from repo root)
tf-init:
	cd infra/terraform && terraform init

tf-plan:
	cd infra/terraform && terraform plan

tf-apply:
	cd infra/terraform && terraform apply

tf-destroy:
	cd infra/terraform && terraform destroy

