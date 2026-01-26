# RAG AI Agent - Analytics Setup Guide

## 📊 Chat Analytics with ClickHouse + Grafana

Your RAG AI Agent now includes a professional analytics system to monitor chat performance, user engagement, and system health. This setup uses:

- **ClickHouse**: High-performance columnar database optimized for analytics (used by Uber, Cloudflare, etc.)
- **Grafana**: Professional visualization and monitoring platform

## 🚀 Quick Start

### 1. Start the Analytics Stack

```bash
docker compose up -d clickhouse grafana
```

Wait for services to be healthy (~30 seconds):

```bash
docker compose ps
```

### 2. Access Dashboards

**Grafana Dashboard**: http://localhost:3000
- Username: `admin`
- Password: `admin` (change on first login)

The dashboard is pre-configured with:
- Real-time message metrics
- Response time percentiles (p50, p90, p95, p99)
- Session statistics
- Tool usage tracking
- Error monitoring
- Top users by activity

### 3. API Access

**Analytics API**: http://localhost:2024/analytics/

Available endpoints:
- `GET /analytics/health` - Health check
- `GET /analytics/metrics/summary?hours=24` - Summary metrics
- `GET /analytics/metrics/response-time` - Response time percentiles
- `GET /analytics/metrics/top-users?limit=10` - Top active users
- `GET /analytics/metrics/popular-tools` - Tool usage stats
- `GET /analytics/metrics/recent-errors?limit=50` - Recent errors

## 📈 Metrics Tracked

### Chat Messages
- Message count (user & assistant)
- Content length
- Token usage
- Response time (duration)
- Model used
- Metadata

### Tool Calls
- Tool invocations
- Execution duration
- Success/failure rate
- Error messages

### Sessions
- Session duration
- Message count per session
- Total tokens per session
- User identification

### Errors
- Error type and frequency
- Error messages
- Stack traces
- Affected threads

## 🔍 Key Features

### High Performance
- **Columnar storage**: Optimized for analytical queries
- **Partitioning**: Data partitioned by month for efficient querying
- **TTL**: Automatic data cleanup after 90 days
- **Materialized views**: Pre-aggregated metrics for instant results

### Real-Time Updates
- Dashboard auto-refreshes every 30 seconds
- Async tracking doesn't block chat responses
- Batch inserts for high throughput

### Scalability
- ClickHouse handles millions of events per second
- Efficient compression (10x+ reduction)
- Horizontal scaling ready

## 🔧 Configuration

### Environment Variables

Create `.env` file or set in docker-compose:

```bash
# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=analytics
CLICKHOUSE_PASSWORD=your_secure_password
CLICKHOUSE_DB=analytics

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password
GRAFANA_ROOT_URL=http://localhost:3000
GRAFANA_ANONYMOUS=false
```

### Data Retention

Default: 90 days. To change, edit `init-db.sql`:

```sql
TTL date + INTERVAL 365 DAY  -- Keep for 1 year
```

## 📊 Sample Queries

### Direct ClickHouse Queries

Access ClickHouse CLI:

```bash
docker compose exec clickhouse clickhouse-client -u analytics --password analytics_password -d analytics
```

#### Top 10 Slowest Responses
```sql
SELECT 
    thread_id,
    duration_ms,
    timestamp
FROM chat_messages
WHERE message_type = 'assistant'
ORDER BY duration_ms DESC
LIMIT 10;
```

#### Hourly Message Volume
```sql
SELECT 
    toStartOfHour(timestamp) as hour,
    count() as messages
FROM chat_messages
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY hour
ORDER BY hour;
```

#### Error Rate by Type
```sql
SELECT 
    error_type,
    count() as occurrences,
    round(count() * 100.0 / (SELECT count() FROM chat_errors WHERE timestamp >= now() - INTERVAL 24 HOUR), 2) as percentage
FROM chat_errors
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY error_type
ORDER BY occurrences DESC;
```

## 🔐 Security Best Practices

1. **Change default passwords** in production
2. **Use strong passwords** for ClickHouse and Grafana
3. **Enable HTTPS** for Grafana in production
4. **Restrict network access** - only allow backend to access ClickHouse
5. **Set up authentication** for Grafana (disable anonymous access)

### Production Password Setup

```bash
# Generate secure passwords
CLICKHOUSE_PASSWORD=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -base64 32)

# Add to .env file
echo "CLICKHOUSE_PASSWORD=$CLICKHOUSE_PASSWORD" >> .env
echo "GRAFANA_PASSWORD=$GRAFANA_PASSWORD" >> .env
```

## 🎯 Dashboard Panels

### Real-Time Stats (Top Row)
- Total Messages (24h)
- Average Response Time
- Total Sessions
- Error Count

### Time Series (Middle)
- Messages per Hour (by type)
- Response Time Percentiles (p50, p90, p95, p99)

### Tables (Bottom)
- Tool Usage Statistics
- Top Users by Activity
- Recent Errors

## 🛠️ Troubleshooting

### ClickHouse Connection Failed
```bash
# Check if ClickHouse is running
docker compose logs clickhouse

# Verify connection
docker compose exec clickhouse wget -O- http://localhost:8123/ping
```

### Grafana Shows No Data
1. Check ClickHouse datasource configuration in Grafana
2. Verify ClickHouse has data: `SELECT count() FROM chat_messages`
3. Check Grafana logs: `docker compose logs grafana`

### Analytics Not Tracking
```bash
# Check backend logs
docker compose logs langgraph-server | grep -i analytics

# Verify ClickHouse tables exist
docker compose exec clickhouse clickhouse-client -u analytics --password analytics_password -d analytics -q "SHOW TABLES"
```

## 📚 Resources

- [ClickHouse Documentation](https://clickhouse.com/docs)
- [Grafana Documentation](https://grafana.com/docs)
- [ClickHouse Performance Tips](https://clickhouse.com/docs/en/operations/tips)

## 🎨 Customizing Dashboards

1. Log into Grafana (http://localhost:3000)
2. Navigate to the "RAG Agent Chat Analytics" dashboard
3. Click the gear icon (⚙️) > Settings
4. Edit panels or add new ones
5. Save the dashboard

Export custom dashboards:
```bash
# From Grafana UI: Dashboard > Share > Export > Save to file
# Then replace: backend/src/analytics/grafana-provisioning/dashboards/rag-agent-analytics.json
```

## 💡 Tips

- Use **time range selector** in Grafana to analyze different periods
- Set up **alerts** in Grafana for high error rates or slow responses
- Export dashboards as **PDFs** for reports
- Create **custom views** for specific metrics you care about
- Use **variables** in dashboards for dynamic filtering

---

**Need Help?** Check the logs or create an issue on GitHub.
