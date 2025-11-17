"""
Bot authentication and authorization module.

Provides role verification and permission checking for Discord users.
"""

from services.bot.auth import cache, permissions, role_checker

__all__ = [
    "cache",
    "permissions",
    "role_checker",
]
