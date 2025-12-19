## Deploying `cloudservice` to a single EC2 instance with Kubernetes (k3s)

This guide shows how to run your existing Docker Hub images on a **single-node Kubernetes cluster** on EC2, without EKS.
It reuses the manifests in `infra/k8s`.

---

## 1. Prerequisites

- EC2 instance already created (see `DEPLOY_EC2.md` for basics):
  - Ubuntu 22.04+
  - Security group inbound:
    - TCP **22** from `0.0.0.0/0` (SSH)
    - TCP **80** from `0.0.0.0/0` (HTTP / Ingress)
- Docker images pushed to Docker Hub:
  - `luukmn/cloudservice-gateway:latest`
  - `luukmn/cloudservice-history:latest`
  - `luukmn/cloudservice-frontend:latest`
- Locally, you have the repo with `infra/k8s` if you want to copy the manifests via `scp`.

---

## 2. Install k3s on the EC2 instance

SSH to the EC2 instance:

```bash
ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>
```

Install k3s (single-node Kubernetes with Traefik ingress already included):

```bash
curl -sfL https://get.k3s.io | sh -
```

Verify the cluster:

```bash
sudo kubectl get nodes
```

You should see one node in `Ready` state.

---

## 3. Copy Kubernetes manifests to EC2

From your local machine (where the repo lives), copy the `infra/k8s` directory:

```bash
scp -i /path/to/key.pem -r /path/to/cloudservice/infra/k8s ubuntu@<EC2_PUBLIC_IP>:~/k8s
```

On the EC2 instance:

```bash
cd ~/k8s
ls
```

You should see files like `namespace.yaml`, `nats.yaml`, `gateway.yaml`, `history.yaml`, `frontend.yaml`, `ingress.yaml`, `history-pvc.yaml`.

---

## 4. Deploy cloudservice onto k3s

Apply manifests in order:

```bash
cd ~/k8s

sudo kubectl apply -f namespace.yaml
sudo kubectl apply -f nats.yaml
sudo kubectl apply -f history-pvc.yaml
sudo kubectl apply -f history.yaml
sudo kubectl apply -f gateway.yaml
sudo kubectl apply -f frontend.yaml
sudo kubectl apply -f ingress.yaml
```

Check resources:

```bash
sudo kubectl get pods -n cloudservice-demo
sudo kubectl get svc -n cloudservice-demo
sudo kubectl get ingress -n cloudservice-demo
```

All pods should eventually show `STATUS = Running`.

> Note: The manifests are already configured to pull your Docker Hub images (`<DockerHubUsername>/cloudservice-*`) and to use in-cluster DNS names (e.g. `gateway.cloudservice-demo.svc.cluster.local`).

---

## 5. Access the application

- k3s installs **Traefik** as the ingress controller by default and binds it to **port 80** on the node.
- `infra/k8s/ingress.yaml` routes:
  - `/` → `frontend` service (port 80)
  - `/gateway` → `gateway` service (port 8000)
  - `/history` → `history` service (port 9000)

From your browser, simply open:

```text
http://<EC2_PUBLIC_IP>/
```

Make sure the EC2 security group allows **TCP 80**.

---

## 6. Day‑2 operations (updates, restarts)

### 6.1 Restart deployments

From the EC2 instance:

```bash
sudo kubectl rollout restart deploy/gateway -n cloudservice-demo
sudo kubectl rollout restart deploy/history -n cloudservice-demo
sudo kubectl rollout restart deploy/frontend -n cloudservice-demo
```

### 6.2 Check health

```bash
sudo kubectl get pods -n cloudservice-demo
sudo kubectl logs deploy/gateway -n cloudservice-demo
sudo kubectl logs deploy/history -n cloudservice-demo
sudo kubectl logs deploy/frontend -n cloudservice-demo
```

### 6.3 Deploy new versions (after code changes)

1. Locally, rebuild and push:

   ```bash
   cd /path/to/cloudservice
   make push-images
   ```

2. On EC2, trigger new pods to pull latest tags:

   ```bash
   ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>

   cd ~/k8s
   sudo kubectl rollout restart deploy/gateway -n cloudservice-demo
   sudo kubectl rollout restart deploy/history -n cloudservice-demo
   sudo kubectl rollout restart deploy/frontend -n cloudservice-demo
   ```

---

## 7. After EC2 stop/start

If you **stop** and later **start** the EC2 instance:

- k3s and your Kubernetes resources (deployments, services, ingress) are preserved on disk.
- On boot, k3s will come back up and recreate pods as needed.

Check status after a restart:

```bash
ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>

sudo kubectl get pods -n cloudservice-demo
sudo kubectl get ingress -n cloudservice-demo
```

If the public IP changed and your frontend or CORS settings depend on the IP, rebuild/push images or adjust env/config just as you would for the pure-Docker setup.


