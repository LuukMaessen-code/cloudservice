## Deploying `cloudservice` to AWS EC2 with Docker

This guide assumes:
- You have Docker + Make + Node (for building) installed **locally**.
- You have a Docker Hub account (e.g. `luukmn`).
- You want to run everything on a single EC2 instance using **Docker Hub images**, not git clone.

---

## 1. One‑time local setup (build & push images)

### 1.1 Configure frontend URLs for EC2

In `frontend/web/.env.production` (create if it does not exist), set:

```bash
VITE_GATEWAY_URL=http://<EC2_PUBLIC_IP>:8000
VITE_HISTORY_URL=http://<EC2_PUBLIC_IP>:9000
```

- Replace `<EC2_PUBLIC_IP>` with your instance’s public IP or DNS (e.g. `16.16.217.223`).
- This controls where the static frontend will send WebSocket and history requests.

### 1.2 Build & push images to Docker Hub

From the `cloudservice` repo root on your local machine:

```bash
cd /path/to/cloudservice

# Log in to Docker Hub if needed
docker login

# Build + push all images using the Makefile
make push-images
```

This creates and pushes:
- `luukmn/cloudservice-gateway:latest`
- `luukmn/cloudservice-history:latest`
- `luukmn/cloudservice-frontend:latest`

You only need to redo this when you change code or config and want a new version on EC2.

---

## 2. One‑time EC2 setup

### 2.1 Launch EC2 instance

In the AWS console:

- AMI: **Ubuntu 22.04 LTS** (or similar).
- Instance type: e.g. `t3.micro` or `t3.small`.
- Key pair: create/select a key and keep the `.pem` safe.
- Security group **inbound rules** (for demo):
  - TCP **22** from `0.0.0.0/0` (SSH).
  - TCP **80** from `0.0.0.0/0` (frontend).
  - TCP **8000** from `0.0.0.0/0` (gateway).
  - TCP **9000** from `0.0.0.0/0` (history).
  - (Optional) TCP **4222**, **8222** from `0.0.0.0/0` (NATS, monitoring).

Note the **Public IPv4 address** or **Public DNS** (used as `<EC2_PUBLIC_IP>` in URLs).

### 2.2 SSH into the instance

On your local machine:

```bash
ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>
```

### 2.3 Install Docker and Docker Compose V2

On the EC2 instance:

**Option A: Install Docker from Docker's official repository (recommended - includes Compose V2):**

```bash
# Remove old docker-compose if installed
sudo apt-get remove -y docker-compose || true

# Install prerequisites
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Docker Compose plugin
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker
```

**Option B: If Docker is already installed, add Docker's repository and install Compose V2 plugin:**

```bash
# Remove old standalone docker-compose
sudo apt-get remove -y docker-compose || true

# Install prerequisites
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-compose-plugin
```

Verify installation:

```bash
docker --version
docker compose version
```

You should see Docker Compose V2 (e.g., `v2.x.x`). Note: Use `docker compose` (with space) instead of `docker-compose` (with hyphen).

---

## 3. Upgrading from old docker-compose (if you already have it installed)

If you already have the old `docker-compose` (v1) installed and are experiencing the `ContainerConfig` error, upgrade to Docker Compose V2:

```bash
# Stop any running containers
cd ~/cloudservice
sudo docker-compose down || true

# Remove old docker-compose
sudo apt-get remove -y docker-compose

# Install prerequisites
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package list
sudo apt-get update -y

# Install Docker Compose V2 plugin
sudo apt-get install -y docker-compose-plugin

# Verify
docker compose version
```

Now use `docker compose` (with space) instead of `docker-compose` (with hyphen) for all commands. This permanently fixes the `ContainerConfig` bug.

---

## 4. EC2 runtime setup (docker compose)

On the EC2 instance:

```bash
mkdir -p ~/cloudservice
cd ~/cloudservice
```

Create `docker-compose.yml`:

```bash
nano docker-compose.yml
```

Paste:

```yaml
services:
  nats:
    image: nats:2.10-alpine
    command: ["-js", "-m", "8222"]
    ports:
      - "4222:4222"
      - "8222:8222"
    networks: [cloudservice]

  gateway:
    image: DH_USERNAME/cloudservice-gateway:latest
    environment:
      NATS_URL: "nats://nats:4222"
      HISTORY_API_URL: "http://history:9000"
      PYTHONPATH: "/app:/app/packages"
    depends_on:
      - nats
      - history
    ports:
      - "8000:8000"
    networks: [cloudservice]

  history:
    image: DH_USERNAME/cloudservice-history:latest
    environment:
      NATS_URL: "nats://nats:4222"
      STORAGE_PATH: "/data/history"
      PYTHONPATH: "/app:/app/packages"
      ALLOWED_ORIGINS: '["http://<EC2_PUBLIC_IP>"]'
    volumes:
      - ./data:/data
    depends_on:
      - nats
    ports:
      - "9000:9000"
    networks: [cloudservice]

  frontend:
    image: DH_USERNAME/cloudservice-frontend:latest
    depends_on:
      - gateway
      - history
    ports:
      - "80:80"
    networks: [cloudservice]

networks:
  cloudservice: {}
```

Important:
- Replace `<EC2_PUBLIC_IP>` in `ALLOWED_ORIGINS` with your **actual** IP or DNS.
- Replace `DH_USERNAME` for all images with your dockerhub username
- Make sure you used the same IP/DNS in `.env.production` when building the frontend image.

Create the data directory (for history JSONL files):

```bash
mkdir -p data
```

Pull images and start:

```bash
sudo docker compose pull
sudo docker compose up -d
sudo docker compose ps
```

> **Note**: We use `docker compose` (with space, V2) instead of `docker-compose` (with hyphen, V1). This avoids the `ContainerConfig` bug that affects the old version.

Now browse to:
- `http://<EC2_PUBLIC_IP>/` → frontend
- `http://<EC2_PUBLIC_IP>:8000/docs` → gateway docs
- `http://<EC2_PUBLIC_IP>:9000/healthz` → history health

---

## 5. Restarting an existing EC2 instance

If you **stop** and later **start** the same EC2 instance:

1. SSH back in:

   ```bash
   ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>
   ```

2. Go to the compose directory and start the stack:

   ```bash
   cd ~/cloudservice
   sudo docker compose up -d
   sudo docker compose ps
   ```

3. Open `http://<EC2_PUBLIC_IP>/` in your browser.

> Note: If the public IP changes (common when you stop/start an instance without an Elastic IP), update:
> - `frontend/web/.env.production` locally (`VITE_GATEWAY_URL`, `VITE_HISTORY_URL`),
> - `ALLOWED_ORIGINS` in `docker-compose.yml` on EC2,
> then rebuild/push images and `docker compose pull` again.

---

## 6. Rebuilding after code changes

When you change code locally and want a fresh deploy:

1. Update `frontend/web/.env.production` if the EC2 address changed.
2. From `cloudservice` root on your machine:

   ```bash
   REGISTRY=luukmn TAG=latest make push-images
   ```

3. On EC2:

   ```bash
   cd ~/cloudservice
   sudo docker compose pull
   sudo docker compose up -d
   sudo docker compose ps
   ```

That’s it: this file should be all you need to bring up the app from scratch or restart it later. 


