# ThermaCity Production Deployment Plan (Vercel + Oracle Cloud)

This document outlines the exact architecture and step-by-step process for deploying the ThermaCity web application and Machine Learning backend. **Target Cost: $0/month while remaining within Always Free limits.**

## Architecture Overview

```mermaid
graph TD
    User([User Browser]) -->|HTTPS| Frontend[Vercel: React UI]
    Frontend -->|HTTPS API call| Caddy[Caddy Reverse Proxy]
    
    subgraph Oracle Cloud Always Free (Ampere A1 ARM64)
        Caddy -->|HTTP internal| Backend[FastAPI: 1 worker]
        ML[113MB scikit-learn model]
        Backend --- ML
    end
    
    Backend -->|PostgreSQL connection| DB[(Supabase PostGIS)]
```

### Why this architecture?
1. **Target Cost:** $0/month while remaining within eligible Oracle Cloud Always Free limits. The Always Free resources continue perpetually even after the 30-day trial ends.
2. **Substantial Compute:** Oracle's Ampere A1 ARM64 Always Free tier currently provides **1,500 OCPU-hours and 9,000 GB-hours per month**, which is equivalent to a continuously running VM with **2 OCPUs and 12 GB of RAM**. The 12 GB allocation provides substantial memory headroom and makes model-related OOM substantially less likely, but memory usage will still be measured after deployment. *(Note: Oracle frequently experiences "Out of Capacity" errors for free A1 instances depending on the region, which may require retries or selecting a different availability domain).*

---

## Phase 0: ARM64 Compatibility Validation

Before committing to the Oracle ARM deployment, we must verify that our specific Python stack runs cleanly on `aarch64`.

**Test:**
- Verify `requirements.txt` specifically for native/C-extension libraries (e.g., NumPy, Pandas, scikit-learn).
- Verify the `.joblib` model successfully unpickles and runs a prediction on ARM architecture.

If geospatial or ML dependencies fail to compile/run on ARM without complex workarounds, first resolve the specific dependency issue or rebuild the environment for ARM64. Do *not* use a 1 GB fallback (GCP/Oracle AMD) as a preferred production deployment, as 1 GB is too tight for this ML stack.

---

## Prerequisites (User Action Required)

### 1. Vercel (Frontend)
- Create a free account at [Vercel.com](https://vercel.com).

### 2. Oracle Cloud (Backend)
- Sign up for Oracle Cloud Free Tier.
- Provision a Compute Instance:
  - **Shape:** `VM.Standard.A1.Flex` (Ampere A1 ARM).
  - **Resources:** Allocate 2 OCPUs and 12 GB RAM.
  - **OS:** Ubuntu 24.04 LTS (aarch64/ARM64 version).
  - **Networking:** Create a **Network Security Group (NSG)** that allows TCP 80 and 443 (from `0.0.0.0/0`) and TCP 22 (restricted to your IP). Attach this NSG to the instance.
- **CRITICAL - Reserved IP:** Do not use the ephemeral public IP. In the Oracle console, reserve a **Reserved Public IPv4 Address** and assign it to the VM so it survives reboots. (Monitor your OCI billing page to ensure no stray charges).
- Save the generated SSH Private Key securely.

### 3. Domains & Supabase
- Have the Supabase `DATABASE_URL` ready.
- Point your API subdomain (e.g., `api.thermacity.com`) to the **Reserved Public IP** of your Oracle VM via your DNS provider.

---

## Automated Deployment Steps (Agent Action Required)

### Phase 1: Containerize the Backend
1. Create a `Dockerfile` targeting ARM64 (`python:3.11-slim`).
2. Configure Uvicorn to start with **1 worker** initially. (We will measure memory in production before deciding if scaling is beneficial).
3. Create a `docker-compose.yml`:
   - `caddy`: Exposes ports `80:80` and `443:443`.
   - `fastapi`: Only uses `expose: "8000"` (internal Docker network only). It must **not** be publicly accessible via `8000:8000`.

### Phase 2: Deploy Backend to Oracle Cloud via SSH
1. SSH into the remote VM using the provided private key: `ssh -i private.key ubuntu@<ORACLE_IP>`.
2. Setup the VM OS Firewall:
   - Carefully inspect the Ubuntu OS firewall (e.g., via `ufw` or `iptables`) and allow ports 80/443 without blindly flushing existing rules. (Ensure `netfilter-persistent` is used if manually editing iptables).
   - Install Docker & Git.
   - Clone the repository.
   - **Create the Production `.env` file:** Do NOT blindly copy your local `.env`. Create a fresh `.env` directly on the VM containing ONLY the variables required by the backend (e.g., `DATABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`). Ensure this file is gitignored.
3. Start the services:
   - Configure Caddy (`Caddyfile`) to map `https://api.yourdomain.com` to `http://fastapi:8000`.
   - Run `docker compose up -d`.

### Phase 3: Deploy Frontend to Vercel
1. In the Vercel dashboard (or via CLI), add all required environment variables:
   - `VITE_API_URL` (pointing to the secure Caddy URL, e.g., `https://api.yourdomain.com`)
   - `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (Safe to expose to the frontend).
   - **WARNING:** Never put private keys (like `SUPABASE_SERVICE_ROLE_KEY` or `DATABASE_URL`) into Vercel frontend variables.
2. Run `vercel --prod` to deploy.
