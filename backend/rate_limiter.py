"""
Rate Limiting Utility for Authentication & Sensitive Endpoints.

Implements an in-memory sliding-window rate limiter per client IP / key
to prevent brute-force attacks and credential enumeration.
"""

import time
from collections import defaultdict
from flask import request, current_app

# Store attempt timestamps: { key: [timestamp1, timestamp2, ...] }
_attempts = defaultdict(list)


def get_client_ip():
    """
    Returns the client IP address.
    When ProxyFix is active in production, request.remote_addr reflects
    the verified client IP from the trusted proxy.
    """
    return request.remote_addr or "127.0.0.1"


def is_rate_limited(key, max_attempts=5, window_seconds=300):
    """
    Checks if a given key has exceeded max_attempts within window_seconds.
    Returns (True, retry_after) if rate-limited, or (False, 0) if allowed.
    """
    if current_app and current_app.config.get('TESTING') and not current_app.config.get('ENFORCE_RATE_LIMIT_IN_TESTS'):
        return False, 0

    from backend.config import Config
    if not Config.IS_PRODUCTION and ('127.0.0.1' in key or 'localhost' in key):
        if not (current_app and current_app.config.get('ENFORCE_RATE_LIMIT_IN_TESTS')):
            max_attempts = 50

    now = time.time()
    cutoff = now - window_seconds
    timestamps = _attempts[key]

    # Filter out expired attempts
    valid_timestamps = [t for t in timestamps if t > cutoff]
    _attempts[key] = valid_timestamps

    if len(valid_timestamps) >= max_attempts:
        oldest = valid_timestamps[0]
        retry_after = int(oldest + window_seconds - now) + 1
        return True, max(1, retry_after)

    return False, 0


def record_attempt(key):
    """Records an attempt timestamp for the given key."""
    _attempts[key].append(time.time())


def reset_attempts(key):
    """Resets all attempts for a given key (e.g. after successful login)."""
    if key in _attempts:
        del _attempts[key]


def clear_all_rate_limits():
    """Clears all rate limit records (useful for testing)."""
    _attempts.clear()
