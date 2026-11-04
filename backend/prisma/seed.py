"""Reference seed values for PostgreSQL/Prisma deployments.

The normal course demo uses ``python seed.py`` and the in-memory repository.
This file documents the same initial accounts and level rules for a future
generated Prisma seed command.
"""

SEED_LEVELS = [
    {"level_name": "普通会员", "min_points": 0, "max_points": 999, "sort_no": 1},
    {"level_name": "银牌会员", "min_points": 1000, "max_points": 4999, "sort_no": 2},
    {"level_name": "金牌会员", "min_points": 5000, "max_points": 9999, "sort_no": 3},
    {"level_name": "钻石会员", "min_points": 10000, "max_points": None, "sort_no": 4},
]

DEMO_ADMIN = {"admin_name": "admin", "password": "Admin123!", "role_code": "SUPER_ADMIN"}

