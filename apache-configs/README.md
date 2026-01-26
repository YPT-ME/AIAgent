# Apache Reverse Proxy Configuration

## Architecture

- `yourdomain.com` → Chat UI (port 3001)
- `api.yourdomain.com` → Backend API (port 2024)

## Quick Setup

### 1. Edit domains in config files

```bash
# agent.conf: ServerName yourdomain.com
# agentapi.conf: ServerName api.yourdomain.com
```

### 2. Install

```bash
# Copy configs
sudo cp agent.conf agentapi.conf /etc/apache2/sites-available/

# Enable modules
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite headers

# Enable sites
sudo a2ensite agent.conf agentapi.conf

# Test and reload
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### 3. Update .env

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
LANGGRAPH_API_KEY=your-secret-key
NEXT_PUBLIC_API_KEY=your-secret-key
NEXT_PUBLIC_ASSISTANT_ID=rag_agent
```

### 4. Start Docker

```bash
docker compose up -d --build agent-chat-ui
```

## Cloudflare Setup

### DNS
- Type: `A` | Name: `@` | IP: `YOUR_IP` | Proxy: ON
- Type: `A` | Name: `api` | IP: `YOUR_IP` | Proxy: ON

### Settings
- SSL/TLS → **Flexible** (no server cert needed)
- Network → **WebSockets: ON**

### SSL Options

**Flexible** (recommended):
- No server certificates required
- Use configs as-is

**Full/Full Strict**:
```bash
sudo a2enmod ssl
sudo certbot --apache -d yourdomain.com -d api.yourdomain.com
# Uncomment <VirtualHost *:443> sections in configs
```

## Troubleshooting

```bash
# Check Apache status
sudo systemctl status apache2

# Check Docker
docker compose ps
docker compose logs -f

# View logs
sudo tail -f /var/log/apache2/error.log

# Test endpoints
curl -I https://yourdomain.com
curl -I https://api.yourdomain.com/health
```

### Common Errors

- **525**: Using Full mode without certificates → Switch to Flexible
- **521**: Apache/Docker not running
- **502**: Docker containers stopped
- **WebSocket**: Enable in Cloudflare Network settings
