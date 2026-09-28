"""Database connection pool optimization (v59).

Uses Django's CONN_MAX_AGE for persistent connections + pgBouncer-friendly settings.
"""
from __future__ import annotations


# Connection pool recommendations for production
POOL_RECOMMENDATIONS = {
    "small": {  # < 10k books
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "PGBOUNCER_POOL_MODE": "transaction",
        "PGBOUNCER_MAX_CLIENT_CONN": 100,
        "PGBOUNCER_DEFAULT_POOL_SIZE": 20,
    },
    "medium": {  # 10k-100k books
        "CONN_MAX_AGE": 120,
        "CONN_HEALTH_CHECKS": True,
        "PGBOUNCER_POOL_MODE": "transaction",
        "PGBOUNCER_MAX_CLIENT_CONN": 200,
        "PGBOUNCER_DEFAULT_POOL_SIZE": 30,
    },
    "large": {  # > 100k books
        "CONN_MAX_AGE": 300,
        "CONN_HEALTH_CHECKS": True,
        "PGBOUNCER_POOL_MODE": "transaction",
        "PGBOUNCER_MAX_CLIENT_CONN": 500,
        "PGBOUNCER_DEFAULT_POOL_SIZE": 50,
    },
}


def get_pool_config(scale: str = "medium") -> dict:
    return POOL_RECOMMENDATIONS.get(scale, POOL_RECOMMENDATIONS["medium"])


def diagnostics() -> dict:
    """Return current DB connection pool settings."""
    from django.conf import settings
    db = settings.DATABASES.get("default", {})
    return {
        "conn_max_age": db.get("CONN_MAX_AGE", 0),
        "conn_health_checks": db.get("CONN_HEALTH_CHECKS", False),
        "engine": db.get("ENGINE", "?"),
        "host": db.get("HOST", "?"),
        "recommendations": POOL_RECOMMENDATIONS,
    }
