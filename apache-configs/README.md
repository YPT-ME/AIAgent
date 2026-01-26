# Apache Reverse Proxy Configuration

## Architecture

- **Port 80**: Serves `/var/www/html` for Let's Encrypt SSL challenges and redirects HTTP → HTTPS
- **Port 443**: SSL reverse proxy
  - `yourdomain.com` → Chat UI (port 3001)
  - `api.yourdomain.com` → Backend API (port 2024)

## Quick Setup

### 1. Edit domains in config files

```bash
# agentapp.conf: ServerName yourdomain.com
# agentapi.conf: ServerName api.yourdomain.com
```

### 2. Install Apache configs

```bash
# Copy configs
sudo cp agentapp.conf agentapi.conf /etc/apache2/sites-available/

# Enable required modules
sudo a2enmod ssl proxy proxy_http proxy_wstunnel rewrite headers

# Enable sites
sudo a2ensite agentapp.conf agentapi.conf

# Test configuration
sudo apache2ctl configtest
```

### 3. Generate SSL certificates with Let's Encrypt

```bash
# Install certbot if not already installed
sudo apt update && sudo apt install certbot python3-certbot-apache -y

# Generate certificates (no email prompt, auto HTTP→HTTPS redirect)
sudo certbot --apache --non-interactive --agree-tos --register-unsafely-without-email --redirect -d avideoagent.ypt.me -d avideoagentapi.ypt.me

# Reload Apache
sudo systemctl reload apache2
```

**Note**: Certbot will automatically configure the SSL certificates in the Apache configs.

### 4. Update .env

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
LANGGRAPH_API_KEY=your-secret-key
NEXT_PUBLIC_API_KEY=your-secret-key
NEXT_PUBLIC_ASSISTANT_ID=rag_agent
```

### 5. Start Docker

```bash
docker compose up -d --build agent-chat-ui
```

## SSL Certificate Renewal

Certbot auto-renews certificates. To test renewal:

```bash
sudo certbot renew --dry-run
```

Renewal happens automatically via systemd timer.

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
