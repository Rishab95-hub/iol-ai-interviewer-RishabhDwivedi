# Deployment Guide

This guide provides step-by-step instructions for deploying the IOL AI Interviewer to various platforms.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Docker Deployment](#docker-deployment)
- [Heroku Deployment](#heroku-deployment)
- [AWS Deployment](#aws-deployment)
- [Railway Deployment](#railway-deployment)
- [Manual VPS Deployment](#manual-vps-deployment)

---

## Prerequisites

- Git repository with your code
- OpenAI API key
- PostgreSQL database (managed or self-hosted)
- Domain name (optional, for production)

---

## Environment Variables

All deployment methods require these environment variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Application
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=generate-a-strong-random-key

# CORS (adjust for your domain)
CORS_ORIGINS=["https://your-domain.com"]

# Optional: Redis
REDIS_URL=redis://host:6379
```

### Generating SECRET_KEY

```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## Docker Deployment

### 1. Build and Run with Docker Compose

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend alembic upgrade head
```

### 2. Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=false
    ports:
      - "8001:8001"
    depends_on:
      - postgres
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
    restart: always

volumes:
  postgres_data:
```

---

## Heroku Deployment

### 1. Install Heroku CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Windows
# Download from https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Create Heroku App

```bash
# Login
heroku login

# Create app
heroku create iol-ai-interviewer-yourname

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis (optional)
heroku addons:create heroku-redis:mini
```

### 3. Configure Environment

```bash
# Set OpenAI key
heroku config:set OPENAI_API_KEY=sk-your-key

# Set secret key
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Set debug mode
heroku config:set DEBUG=false

# View all config
heroku config
```

### 4. Create Procfile

```procfile
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
release: cd backend && alembic upgrade head
```

### 5. Deploy

```bash
# Add files
git add .
git commit -m "Prepare for Heroku deployment"

# Deploy
git push heroku main

# Check logs
heroku logs --tail

# Open app
heroku open
```

### 6. Scale Dynos (Optional)

```bash
# Check current dynos
heroku ps

# Scale up
heroku ps:scale web=2

# Upgrade dyno type
heroku ps:type professional
```

---

## AWS Deployment

### Option A: AWS Elastic Beanstalk

#### 1. Install EB CLI

```bash
pip install awsebcli
```

#### 2. Initialize EB

```bash
eb init -p python-3.12 iol-ai-interviewer --region us-east-1
```

#### 3. Create Environment

```bash
# Create with database
eb create production-env --database --database.engine postgres

# Set environment variables
eb setenv OPENAI_API_KEY=sk-your-key
eb setenv SECRET_KEY=your-secret-key
eb setenv DEBUG=false
```

#### 4. Deploy

```bash
eb deploy
eb open
```

### Option B: AWS ECS (Elastic Container Service)

#### 1. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t ai-interviewer ./backend

# Tag image
docker tag ai-interviewer:latest your-account.dkr.ecr.us-east-1.amazonaws.com/ai-interviewer:latest

# Push image
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/ai-interviewer:latest
```

#### 2. Create RDS Database

```bash
aws rds create-db-instance \
    --db-instance-identifier ai-interviewer-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username admin \
    --master-user-password your-password \
    --allocated-storage 20
```

#### 3. Create ECS Task Definition

```json
{
  "family": "ai-interviewer-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-account.dkr.ecr.us-east-1.amazonaws.com/ai-interviewer:latest",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql+asyncpg://admin:password@rds-endpoint:5432/interviewer"
        },
        {
          "name": "OPENAI_API_KEY",
          "value": "sk-your-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-interviewer",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 4. Create ECS Service

```bash
aws ecs create-service \
    --cluster your-cluster \
    --service-name ai-interviewer-service \
    --task-definition ai-interviewer-task \
    --desired-count 2 \
    --launch-type FARGATE \
    --load-balancers targetGroupArn=your-tg-arn,containerName=backend,containerPort=8001
```

---

## Railway Deployment

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Login and Initialize

```bash
# Login
railway login

# Initialize project
railway init

# Link to Railway project
railway link
```

### 3. Add Database

```bash
# Add PostgreSQL
railway add --database postgresql

# Get database URL
railway variables
```

### 4. Set Environment Variables

```bash
railway variables set OPENAI_API_KEY=sk-your-key
railway variables set SECRET_KEY=your-secret-key
railway variables set DEBUG=false
```

### 5. Deploy

```bash
# Deploy
railway up

# Check status
railway status

# View logs
railway logs

# Open in browser
railway open
```

---

## Manual VPS Deployment

### 1. Provision VPS

Recommended providers:
- DigitalOcean ($6/month droplet)
- Linode ($5/month Nanode)
- Vultr ($6/month instance)

Specs:
- 2GB RAM minimum
- 1 CPU
- 50GB storage
- Ubuntu 22.04 LTS

### 2. Initial Server Setup

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Create user
adduser interviewer
usermod -aG sudo interviewer

# Setup firewall
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable

# Switch to user
su - interviewer
```

### 3. Install Dependencies

```bash
# Python
sudo apt install python3.12 python3.12-venv python3-pip -y

# PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Nginx
sudo apt install nginx -y

# Certbot (for SSL)
sudo apt install certbot python3-certbot-nginx -y
```

### 4. Setup PostgreSQL

```bash
sudo -u postgres psql

CREATE DATABASE ai_interviewer;
CREATE USER interviewer WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE ai_interviewer TO interviewer;
\q
```

### 5. Clone and Setup Application

```bash
# Clone repository
git clone https://github.com/yourusername/iol-ai-interviewer-yourname.git
cd iol-ai-interviewer-yourname

# Create virtual environment
cd backend
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp ../.env.example ../.env
nano ../.env  # Edit with your values

# Run migrations
alembic upgrade head
```

### 6. Setup Systemd Service

```bash
sudo nano /etc/systemd/system/ai-interviewer.service
```

```ini
[Unit]
Description=AI Interviewer Backend
After=network.target postgresql.service

[Service]
Type=simple
User=interviewer
WorkingDirectory=/home/interviewer/iol-ai-interviewer-yourname/backend
Environment="PATH=/home/interviewer/iol-ai-interviewer-yourname/backend/venv/bin"
ExecStart=/home/interviewer/iol-ai-interviewer-yourname/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ai-interviewer
sudo systemctl start ai-interviewer
sudo systemctl status ai-interviewer
```

### 7. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/ai-interviewer
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    client_max_body_size 100M;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ai-interviewer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Setup SSL with Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 9. Setup Automatic Backups

```bash
# Create backup script
nano ~/backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U interviewer ai_interviewer > ~/backups/db_$DATE.sql
find ~/backups -name "db_*.sql" -mtime +7 -delete
```

```bash
chmod +x ~/backup.sh

# Add to crontab
crontab -e
# Add line: 0 2 * * * /home/interviewer/backup.sh
```

---

## Post-Deployment Checklist

- [ ] Database migrations ran successfully
- [ ] Environment variables configured correctly
- [ ] SSL certificate installed (production)
- [ ] Health check endpoint responding: `/health`
- [ ] API documentation accessible: `/docs`
- [ ] Test interview flow end-to-end
- [ ] Monitoring setup (optional: Sentry, DataDog)
- [ ] Backups configured
- [ ] Firewall rules configured
- [ ] Rate limiting enabled (optional)
- [ ] CDN configured (optional: CloudFlare)

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check API health
curl https://your-domain.com/health

# Check database connection
psql -h localhost -U interviewer -d ai_interviewer -c "SELECT 1"

# Check logs
sudo journalctl -u ai-interviewer -f
```

### Performance Monitoring

Consider integrating:
- **Sentry**: Error tracking
- **DataDog**: APM and metrics
- **Grafana**: Custom dashboards
- **PostgreSQL slow query log**: Database optimization

### Backup Strategy

- **Daily**: Database dumps
- **Weekly**: Full system backup
- **Monthly**: Test restore procedure
- **S3 storage**: Store backups off-site

---

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u ai-interviewer -n 50

# Check if port is in use
sudo lsof -i :8001

# Verify environment variables
sudo systemctl show ai-interviewer --property=Environment
```

### Database connection issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U interviewer -d ai_interviewer

# Check DATABASE_URL format
echo $DATABASE_URL
```

### High memory usage

```bash
# Check memory
free -h

# Reduce workers in systemd service
# Edit ExecStart line: --workers 2 (instead of 4)
```

---

## Scaling Considerations

### Vertical Scaling
- Increase server RAM/CPU
- Optimize database queries
- Add Redis caching

### Horizontal Scaling
- Load balancer (Nginx, HAProxy)
- Multiple backend instances
- Database read replicas
- Separate audio storage (S3)

---

**Need help?** Open an issue or consult the main README.md
