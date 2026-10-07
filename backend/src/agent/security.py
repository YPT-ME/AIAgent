"""
Security and Monitoring Middleware for RAG Agent

This module provides security features including:
- Request logging with cost tracking
- Rate limiting per user
- Input validation
- Usage monitoring
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Simple in-memory rate limiting (for production, use Redis)
class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests = max_requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
        
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limit"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for user {user_id}. "
                f"Requests in last minute: {len(self.requests[user_id])}"
            )
            return False
        
        # Add new request
        self.requests[user_id].append(now)
        return True
    
    def get_remaining(self, user_id: str) -> int:
        """Get remaining requests for user"""
        now = time.time()
        minute_ago = now - 60
        recent = [r for r in self.requests[user_id] if r > minute_ago]
        return max(0, self.max_requests - len(recent))


class UsageMonitor:
    """Monitor API usage and costs"""
    
    def __init__(self):
        self.daily_stats = defaultdict(lambda: {
            'requests': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'estimated_cost': 0.0
        })
        
    def log_request(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "gpt-6-luna"
    ):
        """Log a request with token usage"""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{today}:{user_id}"
        
        self.daily_stats[key]['requests'] += 1
        self.daily_stats[key]['input_tokens'] += input_tokens
        self.daily_stats[key]['output_tokens'] += output_tokens
        
        # Estimate cost (GPT-6 Luna pricing)
        # Input: $0.10 / 1M tokens, Output: $0.50 / 1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.50
        cost = input_cost + output_cost
        
        self.daily_stats[key]['estimated_cost'] += cost
        
        logger.info(
            f"Request logged - User: {user_id[:8]}..., "
            f"Tokens: {input_tokens}+{output_tokens}, "
            f"Cost: ${cost:.4f}, "
            f"Daily total: ${self.daily_stats[key]['estimated_cost']:.2f}"
        )
        
        # Alert if daily cost is high
        if self.daily_stats[key]['estimated_cost'] > 10.0:
            logger.warning(
                f"HIGH COST ALERT! User {user_id[:8]}... has spent "
                f"${self.daily_stats[key]['estimated_cost']:.2f} today"
            )
    
    def get_daily_stats(self, user_id: Optional[str] = None) -> dict:
        """Get daily statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if user_id:
            key = f"{today}:{user_id}"
            return self.daily_stats.get(key, {
                'requests': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'estimated_cost': 0.0
            })
        
        # Aggregate all users for today
        total = {
            'requests': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'estimated_cost': 0.0,
            'unique_users': 0
        }
        
        for key, stats in self.daily_stats.items():
            if key.startswith(today):
                total['requests'] += stats['requests']
                total['input_tokens'] += stats['input_tokens']
                total['output_tokens'] += stats['output_tokens']
                total['estimated_cost'] += stats['estimated_cost']
                total['unique_users'] += 1
        
        return total


# Global instances
rate_limiter = RateLimiter(max_requests_per_minute=10)
usage_monitor = UsageMonitor()

logger.info("Security and monitoring middleware initialized")
