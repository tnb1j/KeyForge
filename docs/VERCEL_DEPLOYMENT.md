# 100% Free-Tier Vercel Deployment Guide for KeyForge

This guide demonstrates how to deploy KeyForge to **Vercel** with a **100% free-tier cloud PostgreSQL database** and free global SSL.

---

## 🏗️ Architecture on Free Tier

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                         VERCEL                              │
 │   • Global Edge Network (CDN) for Web Admin Dashboard       │
 │   • Serverless Python Runtime for KeyForge REST API         │
 │   • Automatic Free SSL & Custom Domain Support              │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Encrypted TLS Connection)
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │              FREE CLOUD POSTGRESQL DATABASE                 │
 │   • Neon.tech (Free Serverless Postgres - 0.5 GB storage)   │
 │   • OR Supabase (Free Tier PostgreSQL - 500 MB storage)     │
 └─────────────────────────────────────────────────────────────┘
```

**Total Monthly Cost**: **$0.00 / month** (Forever Free Tiers).

---

## 📋 Step 1: Create a Free Cloud Database (2 minutes)

Since serverless runtimes are stateless, connect KeyForge to a free cloud PostgreSQL database:

### Option A: Neon.tech (Recommended)
1. Go to [neon.tech](https://neon.tech) and sign up with your GitHub account.
2. Click **Create Project**, name it `keyforge`, and click **Create**.
3. Copy the **Connection String** provided on your dashboard:
   ```text
   postgresql://alex:AbC123dEf@ep-cool-frog-123456.us-east-2.aws.neon.tech/keyforge?sslmode=require
   ```

### Option B: Supabase
1. Go to [supabase.com](https://supabase.com) and create a free project.
2. Under **Project Settings $\to$ Database $\to$ Connection String (URI)**, copy the URI.

---

## 🚀 Step 2: Deploy to Vercel (1-Click or Import)

1. Go to [vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **Add New... $\to$ Project**.
3. Select your repository: **`tnb1j/KeyForge`**.
4. In the **Environment Variables** section, add:
   * **`KEYFORGE_DB_URL`**: Your PostgreSQL connection string from Step 1.
   * **`KEYFORGE_JWT_SECRET`**: A random secret string (e.g. `c4e5f7a8b9d0e1f2a3b4c5d6e7f8a9b0`).
   * **`KEYFORGE_ADMIN_USER`**: Your desired admin username (e.g. `admin`).
   * **`KEYFORGE_ADMIN_PASS`**: Your desired strong admin password (e.g. `MySecureAdmin2026!`).
5. Click **Deploy**!

---

## ✨ Step 3: Access Your Live Deployment

Once Vercel finishes building (typically ~45 seconds):
* **Web Admin Dashboard**: `https://<your-project>.vercel.app/dashboard`
* **Interactive OpenAPI Swagger**: `https://<your-project>.vercel.app/docs`
* **Licensing API Base**: `https://<your-project>.vercel.app/api/v1`

---

## 🔄 Automatic Continuous Deployment

Every time you push new code or updates to your GitHub repository:
```bash
git push origin main
```
Vercel automatically detects the commit, runs the build, and updates your live production deployment seamlessly with zero downtime.
