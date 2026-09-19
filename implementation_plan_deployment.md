# ThermaCity Production Deployment Plan (Vercel + Render)

This document outlines the architecture and process for deploying the ThermaCity web application and Machine Learning backend using a modern PaaS (Platform as a Service) approach.

## Architecture Overview

`mermaid
graph TD
    User([User Browser]) -->|HTTPS| Frontend[Vercel: React UI]
    Frontend -->|HTTPS API call| Backend[Render: FastAPI Web Service]
    Backend -->|PostgreSQL connection| DB[(Supabase PostGIS)]
`

### Why this architecture? (The "Story")
We are ditching the complex, manual Oracle Cloud Virtual Machine in favor of **Render**. 
1. **Zero Server Maintenance:** With Render, you never have to SSH into a Linux machine, you don't have to manage Firewalls (ufw/iptables), and you don't have to manage reverse proxies or SSL certificates (like Caddy). Render handles all of the HTTPS routing and infrastructure automatically.
2. **Automated CI/CD:** Your friend added a ender.yaml file (Infrastructure as Code). This means when you connect your GitHub repo to Render, it will automatically read that file, build the Docker container, and deploy the FastAPI backend. Every time you git push, your server updates automatically!
3. **Vercel for Frontend:** Vercel remains the best-in-class host for React apps, providing a global CDN so the map UI loads instantly anywhere in the world.

---

## Deployment Steps

### 1. Database (Supabase)
- Database is already fully provisioned.
- Ensure the GitHub Action keep-alive.yml continues to ping the DB using the Session pooler (port 5432 or 6543) to prevent pausing.

### 2. Backend (Render)
1. Go to [Render.com](https://render.com) and sign in with GitHub.
2. Click **New** -> **Blueprint**.
3. Select the ThermaCity repository.
4. Render will automatically detect the ender.yaml file your friend created.
5. In the Render dashboard, supply the required Environment Variables:
   - DATABASE_URL: Your Supabase connection string (using the pooler URL we configured earlier).
6. Click **Apply**. Render will automatically build the Dockerfile and start the FastAPI server.

### 3. Frontend (Vercel)
1. Go to [Vercel.com](https://vercel.com) and import the ThermaCity repository.
2. Since this is a monorepo, set the **Root Directory** to rontend.
3. Add the required Environment Variables:
   - VITE_API_URL: The URL Render gives you (e.g., https://thermacity-api.onrender.com).
   - VITE_SUPABASE_URL & VITE_SUPABASE_ANON_KEY.
4. Click **Deploy**. Vercel will build the React app and give you your live domain.
