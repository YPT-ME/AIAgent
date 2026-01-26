-- =====================================================
-- RAG AI Agent - ClickHouse Analytics Database Schema
-- =====================================================
-- This schema is optimized for high-volume chat analytics
-- with support for real-time metrics and historical analysis.
-- =====================================================

-- Create the analytics database
CREATE DATABASE IF NOT EXISTS analytics;

USE analytics;

-- =====================================================
-- Table: chat_messages
-- Tracks all messages in conversations (user & assistant)
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    timestamp DateTime DEFAULT now(),
    thread_id String,
    user_id String,
    message_type LowCardinality(String),  -- 'user' or 'assistant'
    content_length UInt32,
    tokens UInt32,
    duration_ms UInt32,  -- Response time for assistant messages
    model LowCardinality(String),
    metadata String,  -- JSON string for additional data
    date Date DEFAULT toDate(timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, thread_id, timestamp)
TTL date + INTERVAL 90 DAY  -- Keep data for 90 days
SETTINGS index_granularity = 8192;

-- Index for fast user queries
CREATE INDEX IF NOT EXISTS idx_user_id ON chat_messages(user_id) TYPE bloom_filter GRANULARITY 1;

-- =====================================================
-- Table: tool_calls
-- Tracks function/tool invocations during conversations
-- =====================================================
CREATE TABLE IF NOT EXISTS tool_calls (
    timestamp DateTime DEFAULT now(),
    thread_id String,
    tool_name LowCardinality(String),
    duration_ms UInt32,
    success Bool,
    error_message String,
    date Date DEFAULT toDate(timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, tool_name, timestamp)
TTL date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- =====================================================
-- Table: chat_sessions
-- Tracks conversation sessions with aggregate metrics
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    timestamp DateTime DEFAULT now(),
    thread_id String,
    user_id String,
    duration_ms UInt32,
    message_count UInt16,
    total_tokens UInt32,
    date Date DEFAULT toDate(timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, user_id, timestamp)
TTL date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- =====================================================
-- Table: chat_errors
-- Tracks errors and exceptions during conversations
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_errors (
    timestamp DateTime DEFAULT now(),
    thread_id String,
    error_type LowCardinality(String),
    error_message String,
    stack_trace String,
    date Date DEFAULT toDate(timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, error_type, timestamp)
TTL date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- =====================================================
-- Materialized Views for Real-Time Metrics
-- =====================================================

-- Hourly message statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_messages
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, message_type)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    message_type,
    count() AS message_count,
    sum(tokens) AS total_tokens,
    avg(duration_ms) AS avg_duration_ms
FROM chat_messages
GROUP BY hour, message_type;

-- Daily user activity
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_users
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY date
AS SELECT
    toDate(timestamp) AS date,
    uniqState(user_id) AS unique_users,
    countState() AS total_sessions
FROM chat_sessions
GROUP BY date;

-- Tool usage statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_tool_stats
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, tool_name)
AS SELECT
    toDate(timestamp) AS date,
    tool_name,
    count() AS call_count,
    countIf(success) AS success_count,
    countIf(NOT success) AS error_count,
    avg(duration_ms) AS avg_duration_ms
FROM tool_calls
GROUP BY date, tool_name;

-- Error frequency by type
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_error_stats
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, error_type)
AS SELECT
    toDate(timestamp) AS date,
    error_type,
    count() AS error_count
FROM chat_errors
GROUP BY date, error_type;

-- =====================================================
-- Performance Metrics Views
-- =====================================================

-- Response time percentiles (last 24 hours)
CREATE VIEW IF NOT EXISTS v_response_time_percentiles AS
SELECT
    quantile(0.50)(duration_ms) AS p50_ms,
    quantile(0.90)(duration_ms) AS p90_ms,
    quantile(0.95)(duration_ms) AS p95_ms,
    quantile(0.99)(duration_ms) AS p99_ms
FROM chat_messages
WHERE message_type = 'assistant'
  AND timestamp >= now() - INTERVAL 24 HOUR
  AND duration_ms > 0;

-- Top users by activity (last 7 days)
CREATE VIEW IF NOT EXISTS v_top_users AS
SELECT
    user_id,
    count() AS session_count,
    sum(message_count) AS total_messages,
    sum(total_tokens) AS total_tokens
FROM chat_sessions
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY user_id
ORDER BY session_count DESC
LIMIT 100;

-- Most used tools (last 24 hours)
CREATE VIEW IF NOT EXISTS v_popular_tools AS
SELECT
    tool_name,
    count() AS call_count,
    countIf(success) AS success_count,
    round(avg(duration_ms), 2) AS avg_duration_ms,
    round(countIf(success) * 100.0 / count(), 2) AS success_rate
FROM tool_calls
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY tool_name
ORDER BY call_count DESC;

-- Recent errors (last 24 hours)
CREATE VIEW IF NOT EXISTS v_recent_errors AS
SELECT
    timestamp,
    thread_id,
    error_type,
    error_message
FROM chat_errors
WHERE timestamp >= now() - INTERVAL 24 HOUR
ORDER BY timestamp DESC
LIMIT 100;

-- =====================================================
-- Grant permissions to analytics user
-- =====================================================
-- Note: Permissions are handled by CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT
-- The analytics user will have full access to the analytics database
