# Server Configuration Documentation

## Overview

- **Server IP**: 80.87.111.142
- **SSH Port**: 22
- **OS**: Ubuntu (containerized environment)
- **Last Updated**: 2026-05-19

---

## CRITICAL CONSTRAINTS

> **Docker host networking is BROKEN on this server.** Containers with `network_mode: host` cannot bind to privileged ports (< 1024) due to AppArmor restriction on the Docker daemon. This is a known issue — nginx tunnel runs on host instead of in Docker.

> **Always set `net.ipv4.ip_nonlocal_bind=1`** before starting nginx, otherwise bind() to port 8443 will fail.

---

## Directory Structure

```
/opt/                          # Production services
├── nginx-ru-tunnel/           # Nginx tunnel (main reverse proxy)
│   ├── nginx.conf             # Main nginx config (local copy at /etc/nginx/nginx.conf)
│   └── docker-compose.yml     # (not used — host nginx instead)
├── bereg/                     # Bot service (bereg.maxnov.ru)
│   └── docker/
│       └── docker-compose.yml # mikroshagi stack (bot, postgres, redis, n8n, nginx)
├── adminbereg/                # Admin panel service
├── bsc3/                      # BSC3 service (bsc3.ru)
└── remnanode/                 # Xray service (host network mode)

/home/bot/projects/            # Working project directories (DO NOT MODIFY LIGHTLY)
├── prompt-booster/            # PromptBooster service
├── stylist-miniapp/          # Stylist service
└── n8n/                       # N8N service

/etc/
├── nginx/
│   ├── nginx.conf             # ACTIVE nginx config (copied from /opt/nginx-ru-tunnel/nginx.conf)
│   └── sites-enabled/         # Old site configs (disabled, moved to sites-enabled/disabled/)
├── letsencrypt/               # SSL certificates (all domains)
└── sysctl.d/99-nginx.conf    # Persistent sysctl config
```

---

## Nginx Architecture (CURRENT)

### Current Setup: Host Nginx (NOT Docker)

```
Internet (port 443) 
    ↓
iptables PREROUTING + OUTPUT
    redirect tcp:443 → tcp:8443
    ↓
Host Nginx (nginx/1.24.0 Ubuntu)
    listening on port 8443
    config: /etc/nginx/nginx.conf
    ↓
Reverse Proxy (per domain):
├── bereg.maxnov.ru       → http://127.0.0.1:3003 (mikroshagi_bot)
├── admin.bereg.maxnov.ru → http://127.0.0.1:3004 (mikroshagi_admin)
├── bsc3.ru               → http://127.0.0.1:3010 (bsc3-app)
├── promptbooster.ru       → http://172.19.0.2:3000 (prompt-booster-frontend)
└── bot.tatianazhuikova.ru → http://172.18.0.4:8000 (stylist_backend)
```

### Port Mapping

| External Port | Internal Port | Service | Container/Process |
|---------------|---------------|---------|-------------------|
| 443 (HTTPS) | → 8443 | iptables redirect | nginx host |
| 8443 | 8443 | nginx host | nginx on host |
| 3003 | 3003 | bot (bereg) | mikroshagi_bot Docker |
| 3004 | 3001 | admin panel | mikroshagi_admin Docker |
| 3010 | 3000 | bsc3 | bsc3-app-1 Docker |
| 5678 | 5678 | n8n | mikroshagi_n8n Docker |
| 8082 | 3000 | prompt-booster (internal) | prompt-booster-frontend Docker |
| 8081 | 8000 | stylist (internal) | stylist_backend Docker |
| 22 | 22 | SSH | sshd on host |
| 3306 | 3306 | MariaDB | mariadbd on host |
| 30000 | 30000 | Xray China | xray (remnanode Docker, host network) |
| 2223 | 2223 | SSH alternative | MainThread on host |

### DNS Domains (5 active + 1 inactive)

| Domain | SSL Cert | Backend IP | Status |
|--------|----------|------------|--------|
| bereg.maxnov.ru | /etc/letsencrypt/live/bereg.maxnov.ru/ | 127.0.0.1:3003 | ✅ Working |
| admin.bereg.maxnov.ru | /etc/letsencrypt/live/admin.bereg.maxnov.ru/ | 127.0.0.1:3004 | ✅ Working |
| bsc3.ru | /etc/letsencrypt/live/bsc3.ru/ | 127.0.0.1:3010 | ✅ Working |
| promptbooster.ru | /etc/letsencrypt/live/promptbooster.ru/ | 172.19.0.2:3000 | ⚠️ Working (uses Docker internal IP) |
| bot.tatianazhuikova.ru | /etc/letsencrypt/live/bot.tatianazhuikova.ru/ | 172.18.0.4:8000 | ⚠️ Partial (API works, frontend 404) |
| cloudstream.bot.nu | /etc/letsencrypt/live/cloudstream.bot.nu/ | - | ❌ Inactive (stream block removed) |

---

## iptables Configuration

### Current Rules (NAT table)

```bash
# Redirect incoming 443 to 8443 (for nginx)
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443
iptables -t nat -A OUTPUT -p tcp --dport 443 -j REDIRECT --to-port 8443
```

### Persistence

- Installed `iptables-persistent` + `netfilter-persistent`
- Rules saved with: `netfilter-persistent save`
- Rules persist across reboots

---

## sysctl Configuration

### Required for nginx to bind to privileged ports

```bash
# Transient (temporary)
sysctl -w net.ipv4.ip_nonlocal_bind=1

# Persistent (saved in /etc/sysctl.d/99-nginx.conf)
net.ipv4.ip_nonlocal_bind=1
```

---

## Docker Containers (All)

### Active Containers

| Container Name | Image | Status | Ports | Network |
|----------------|-------|--------|-------|---------|
| mikroshagi_bot | docker-bot | Up | 3003:3000 | docker_mikroshagi_net |
| mikroshagi_postgres | postgres:16-alpine | Up (healthy) | 5432 | docker_mikroshagi_net |
| mikroshagi_redis | redis:7-alpine | Up (healthy) | 6379 | docker_mikroshagi_net |
| mikroshagi_admin | adminbereg-admin | Up | 3004:3001 | docker_mikroshagi_net |
| mikroshagi_n8n | n8nio/n8n:latest | Up | 5678:5678 | docker_mikroshagi_net |
| bsc3-app-1 | bsc3-app | Up | 3010:3000 | bridge |
| bsc3-postgres-1 | postgres:16-alpine | Up (healthy) | 5432 | bridge |
| prompt-booster-frontend-1 | prompt-booster-frontend | Up | 3000 | prompt_booster_net |
| prompt-booster-postgres-1 | postgres:14-alpine | Up (healthy) | 5432 | prompt_booster_net |
| prompt-booster-redis-1 | redis:7-alpine | Up | 6379 | prompt_booster_net |
| stylist_backend | stylist-miniapp-backend | Up | 8000 | stylist_net |
| stylist_bot | stylist-miniapp-backend | Up | - | stylist_net |
| stylist_db | postgres:16 | Up | 5432 | stylist_net |
| remnanode | ghcr.io/remnawave/node:latest | Up | host network | NET_ADMIN cap |

### Stopped Containers

| Container Name | Image | Status | Reason |
|----------------|-------|--------|--------|
| prompt-booster-nginx-1 | nginx:alpine | Exited | Stopped (was occupying port 443) |
| stylist_nginx | nginx:stable | Exited | Stopped (was occupying port 443) |
| mikroshagi_nginx | nginx:alpine | Created | Never started (conflicts) |
| nginx-ru-tunnel | nginx:stable | Removed | Not used (host nginx instead) |

---

## Nginx Configuration File

**Location**: `/etc/nginx/nginx.conf` (copied from `/opt/nginx-ru-tunnel/nginx.conf`)

**Important notes**:
- `stream {}` block was REMOVED because host nginx (1.24.0) doesn't have stream module compiled
- Stream functionality (cloudstream) is inactive
- `http2` directive removed from listen statements (deprecated syntax)

**Key sections**:
```nginx
events { worker_connections 2048; }
http {
    # 5 server blocks, one per domain
    # each: listen 80 → redirect to https
    # each: listen 8443 ssl → proxy_pass to backend
}
```

---

## Known Issues & Solutions

### Issue 1: Docker Host Networking Cannot Bind to Privileged Ports

**Problem**: Containers with `network_mode: host` cannot bind to ports < 1024. Docker daemon AppArmor profile blocks this.

**Solution**: Use host nginx instead of Docker container for nginx tunnel.

**Command that works**:
```bash
# Set sysctl
sysctl -w net.ipv4.ip_nonlocal_bind=1

# Start nginx on host
cp /opt/nginx-ru-tunnel/nginx.conf /etc/nginx/nginx.conf
nginx -t && nginx
```

### Issue 2: Docker Internal IPs Change on Reboot

**Problem**: `172.19.0.2` and `172.18.0.4` (prompt-booster and stylist backends) may change after Docker restart.

**Current workaround**: These are hardcoded in nginx.conf. May need to update after reboot.

**Better solution**: Use Docker DNS (container names as hostnames) — not yet implemented.

### Issue 3: bot.tatianazhuikova.ru Frontend Not Working

**Problem**: Only FastAPI backend (172.18.0.4:8000) is proxied. Frontend static files (HTML/JS/CSS) are not served.

**Previous setup**: `stylist_nginx` container served static files from `./frontend` directory.

**Current status**: Frontend returns 404. Only API endpoints work.

**Potential solutions**:
1. Restore `stylist_nginx` container (but conflicts with port 443)
2. Copy frontend files to host and serve from there
3. Keep as-is (API-only mode)

### Issue 4: Cloudstream Inactive

**Problem**: stream block was removed from nginx.conf. cloudstream.bot.nu is not working.

**Previous setup**: nginx stream block proxied 443 → 10443 for xray/cloudstream.

**Status**: Inactive. No current need for this service.

---

## Management Commands

### Start/Stop Host Nginx

```bash
# Check status
ps aux | grep nginx

# Stop
nginx -s stop

# Start
nginx

# Reload config
nginx -s reload

# Test config
nginx -t
```

### iptables Rules

```bash
# Check current rules
iptables -t nat -L -n

# Add redirect (if missing after reboot)
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443
iptables -t nat -A OUTPUT -p tcp --dport 443 -j REDIRECT --to-port 8443

# Save rules
netfilter-persistent save
```

### sysctl

```bash
# Check current value
cat /proc/sys/net/ipv4/ip_nonlocal_bind

# Set transient
sysctl -w net.ipv4.ip_nonlocal_bind=1

# Set persistent (already done)
echo "net.ipv4.ip_nonlocal_bind=1" > /etc/sysctl.d/99-nginx.conf
```

### Docker Containers

```bash
# List all containers
docker ps -a

# Start specific container
docker start <container-name>

# Stop specific container
docker stop <container-name>

# View logs
docker logs <container-name>
```

### Key Directories

```bash
# Nginx config (active)
cat /etc/nginx/nginx.conf

# Nginx config (source)
/opt/nginx-ru-tunnel/nginx.conf

# SSL certificates
ls /etc/letsencrypt/live/

# Disabled nginx sites
ls /etc/nginx/sites-enabled/disabled/
```

---

## Change Log

### 2026-05-19

**Problem**: Admin panel miniapp broken, all nginx-proxied domains failing.

**Root Causes Found**:
1. Multiple nginx processes running simultaneously (host init.d + Docker containers)
2. Port 443 conflicts between containers
3. Docker host networking cannot bind to privileged ports (AppArmor)
4. Host nginx (init.d) auto-started and grabbed port 443
5. Host nginx init.d had no stream module

**Actions Taken**:
1. Stopped all host nginx processes
2. Disabled host nginx from init.d/systemd
3. Stopped prompt-booster-nginx-1 and stylist_nginx containers
4. Removed stream block from nginx.conf (no stream module on host nginx)
5. Set up iptables redirect: 443 → 8443
6. Set sysctl net.ipv4.ip_nonlocal_bind=1
7. Copied /opt/nginx-ru-tunnel/nginx.conf to /etc/nginx/nginx.conf
8. Started host nginx on port 8443
9. Updated nginx.conf to use Docker internal IPs for prompt-booster and stylist
10. Installed iptables-persistent for rule persistence
11. Created /etc/sysctl.d/99-nginx.conf for sysctl persistence

**Current Status**: 4 of 5 domains working, bot.tatianazhuikova.ru partial (API only).

**Next Steps** (not completed):
1. Fix bot.tatianazhuikova.ru frontend (optional)
2. Reboot test to verify persistence
3. Verify all domains work after reboot

---

## IMPORTANT REMINDERS

1. **DO NOT run `docker compose up` for nginx-ru-tunnel** — it won't work due to AppArmor restrictions. Use host nginx instead.

2. **Always set `sysctl -w net.ipv4.ip_nonlocal_bind=1`** before starting nginx after a reboot.

3. **Docker internal IPs (172.19.0.2, 172.18.0.4) may change** after Docker restart. Check with `docker inspect` if domains stop working.

4. **Backup nginx.conf before modifications** — it's the single point of failure for all domains.

5. **/home/bot/projects/ contains working code** — be careful when modifying docker-compose files there.

6. **Cloudstream is inactive** — no current need. Stream block removed to avoid nginx errors.

---

## Future Improvements (Not Implemented)

1. Use Docker container names as hostname for proxy_pass (avoid IP changes)
2. Fix bot.tatianazhuikova.ru frontend (restore static file serving)
3. Add cloudstream stream block back (when needed)
4. Implement proper backup for nginx.conf
5. Consider using DNS-based service discovery for Docker containers