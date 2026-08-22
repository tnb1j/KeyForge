# KeyForge Deployment and Disaster Recovery Guide

## 1. Production Deployment

### Option A: Docker Compose (Recommended)
```bash
docker-compose up -d --build
```

### Option B: Direct Python Service
```bash
python -m pip install -r requirements.txt
python -m keyforge.cli serve --host 0.0.0.0 --port 8000
```

### Reverse Proxy Configuration (Nginx)
```nginx
server {
    listen 443 ssl http2;
    server_name licensing.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/licensing.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/licensing.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 2. Disaster Recovery & Backup

* **Database Backup**:
  * SQLite: Periodic atomic snapshot or backup of `keyforge.db`.
  * PostgreSQL: `pg_dump -Fc keyforge_db > backup_$(date +%Y%m%d).dump`
* **Signing Key Recovery**:
  * All active and rotated Ed25519 signing keys are stored securely in the database vault.
  * Keep an encrypted offsite export of the key vault in an enterprise secret manager (e.g. AWS Secrets Manager, HashiCorp Vault, Azure Key Vault).
* **Emergency Key Compromise Procedure**:
  1. Trigger immediate key rotation via Dashboard or API (`POST /api/v1/keys/{product_id}/rotate`).
  2. Mark the compromised key ID as `revoked` in the vault.
  3. Deploy updated client builds containing the new verification key.
