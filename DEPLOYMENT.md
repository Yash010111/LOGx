# Deployment Guide

Complete guide for deploying LOGx to production.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Local Deployment](#local-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Security Best Practices](#security-best-practices)
7. [Monitoring & Maintenance](#monitoring--maintenance)

---

## System Requirements

### Minimum Specifications

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 8 GB | 16+ GB |
| **Storage** | 50 GB | 100+ GB |
| **GPU** | Optional | NVIDIA CUDA 11.8+ |
| **Python** | 3.10 | 3.11+ |
| **OS** | Windows/Linux/Mac | Linux (Ubuntu 20.04+) |

### Network Requirements

- Outbound HTTPS to Hugging Face API
- Inbound HTTP/HTTPS for web interface
- GPU instances: Outbound to PyTorch/NVIDIA repos

---

## Pre-Deployment Checklist

- [ ] Python 3.10+ installed and verified
- [ ] All dependencies resolved via `uv sync`
- [ ] `.env` file created with `HF_TOKEN`
- [ ] Tests passing: `make test` or `uv run pytest tests/`
- [ ] Code formatted: `make format`
- [ ] Linting clean: `make lint`
- [ ] Git repository initialized and clean
- [ ] SSL certificates obtained (for HTTPS)
- [ ] Database backup if applicable
- [ ] Firewall rules configured

---

## Local Deployment

### Single Machine Deployment

#### Step 1: Setup System

```bash
# Update system packages
Linux/Mac:
  sudo apt update && sudo apt upgrade -y

# Install dependencies
Linux/Mac:
  sudo apt install -y python3.11 python3-pip git

# Install CUDA (optional, for GPU)
  # See: https://developer.nvidia.com/cuda-downloads
```

#### Step 2: Clone & Configure

```bash
# Clone repository
git clone https://github.com/yourusername/logx.git /opt/logx
cd /opt/logx

# Setup environment
cp .env.example .env
# Edit .env with production values
nano .env
```

#### Step 3: Install & Run

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run with production server
pip install gunicorn  # Production WSGI server

# Start application
gunicorn --workers 4 \
         --worker-class sync \
         --bind 0.0.0.0:5000 \
         --timeout 120 \
         --access-logfile - \
         dashboard:app
```

### Using Systemd Service (Linux)

**Create `/etc/systemd/system/logx.service`:**

```ini
[Unit]
Description=LOGx AI Log Analysis Service
After=network.target
Wants=network-online.target

[Service]
Type=notify
User=logx
Group=logx
WorkingDirectory=/opt/logx
ExecStart=/opt/logx/.venv/bin/gunicorn --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    dashboard:app
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
Environment="HF_TOKEN=your_token_here"

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable logx
sudo systemctl start logx
sudo systemctl status logx
```

---

## Docker Deployment

### Prerequisites

- Docker installed
- Docker Compose (optional)

### Build & Run

#### Using Docker

```bash
# Build image
docker build -t logx:latest .

# Run container
docker run -d \
  --name logx-app \
  -p 5000:5000 \
  -e HF_TOKEN=your_token_here \
  --memory=8g \
  logx:latest

# View logs
docker logs -f logx-app
```

#### Using Docker Compose

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f logx

# Stop services
docker-compose down
```

### Docker Registry Deployment

```bash
# Tag image
docker tag logx:latest yourusername/logx:1.0.0
docker tag logx:latest yourusername/logx:latest

# Push to registry
docker login
docker push yourusername/logx:1.0.0
docker push yourusername/logx:latest

# Pull from registry
docker pull yourusername/logx:latest
```

---

## Cloud Deployment

### Azure Container Instances

```bash
# Create resource group
az group create --name logx-rg --location eastus

# Deploy container
az container create \
  --resource-group logx-rg \
  --name logx-app \
  --image yourusername/logx:latest \
  --environment-variables HF_TOKEN=your_token_here \
  --memory 8 \
  --cpu 2 \
  --ports 5000

# Check status
az container show --resource-group logx-rg --name logx-app
```

### AWS ECS

```bash
# Create task definition
aws ecs register-task-definition \
  --family logx-task \
  --container-definitions '[{
    "name": "logx",
    "image": "yourusername/logx:latest",
    "memory": 8192,
    "cpu": 2048,
    "portMappings": [{"containerPort": 5000}],
    "environment": [{"name": "HF_TOKEN", "value": "your_token"}]
  }]'

# Run service
aws ecs create-service \
  --cluster default \
  --service-name logx-service \
  --task-definition logx-task:1 \
  --desired-count 2
```

### Google Cloud Run

```bash
# Build & push image
gcloud builds submit --tag gcr.io/PROJECT_ID/logx

# Deploy
gcloud run deploy logx \
  --image gcr.io/PROJECT_ID/logx \
  --memory 8Gi \
  --cpu 2 \
  --set-env-vars HF_TOKEN=your_token_here \
  --allow-unauthenticated
```

---

## Security Best Practices

### 1. Environment Variables

```bash
# Never hardcode secrets
# Use .env file (excluded from git via .gitignore)
# In production, use secrets manager

# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id logx/hf_token

# Azure Key Vault
az keyvault secret show --vault-name logx-vault --name HF_TOKEN

# Google Secret Manager
gcloud secrets versions access latest --secret="HF_TOKEN"
```

### 2. HTTPS/SSL

```bash
# Use reverse proxy (Nginx)
# Configure Let's Encrypt SSL

# Nginx configuration example:
upstream logx_app {
    server 127.0.0.1:5000;
}

server {
    listen 443 ssl http2;
    server_name logx.example.com;

    ssl_certificate /etc/letsencrypt/live/logx.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/logx.example.com/privkey.pem;

    location / {
        proxy_pass http://logx_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Firewall Rules

```bash
# Allow only necessary ports
# HTTP/HTTPS: 80, 443
# SSH: 22 (admin only)
# Block HuggingFace API (outbound only)

# Linux firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 4. Authentication

```python
# Add basic authentication (in dashboard.py)
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    users = {"admin": "secure_password"}
    return users.get(username) == password

@app.route("/", methods=["GET", "POST"])
@auth.login_required
def index():
    # Protected route
    pass
```

### 5. Rate Limiting

```python
# Add rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/", methods=["POST"])
@limiter.limit("10 per minute")
def index():
    # Rate limited route
    pass
```

---

## Monitoring & Maintenance

### Logging

```bash
# Application logs
docker logs logx-app > app.log 2>&1

# System logs
journalctl -u logx -f

# Nginx logs
tail -f /var/log/nginx/error.log
```

### Health Checks

```bash
# Manual health check
curl http://localhost:5000/

# Automated monitoring with Prometheus
# Add metrics endpoint:

from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

### Updates

```bash
# Pull latest changes
cd /opt/logx
git pull origin main

# Update dependencies
uv sync

# Restart service
sudo systemctl restart logx
```

### Backup Strategy

```bash
# Backup generated reports
rsync -avz logx:/app/reports/ /backup/logx-reports/

# Backup configuration
tar czf backup-logx-$(date +%Y%m%d).tar.gz .env docker-compose.yml

# Generate backup schedule (crontab)
0 2 * * * /backup-script.sh
```

---

## Troubleshooting

### High Memory Usage

```bash
# Monitor memory
docker stats logx-app

# Restart container
docker restart logx-app

# Adjust limits in docker-compose.yml
```

### Slow Response Times

```bash
# Check GPU availability
nvidia-smi

# Monitor CPU/GPU usage
watch -n 1 nvidia-smi

# Increase worker processes
gunicorn --workers 8 dashboard:app
```

### Connection Issues

```bash
# Check network
curl -v https://huggingface.co/

# Verify HF_TOKEN
echo $HF_TOKEN

# Check firewall
sudo ufw status
```

---

## References

- [Flask Deployment](https://flask.palletsprojects.com/deployment/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [OWASP Security Checklists](https://cheatsheetseries.owasp.org/)

---

**Last Updated**: February 26, 2026
