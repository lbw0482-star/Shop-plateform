"""Demo credentials and data for the in-memory course API.

When a PostgreSQL database is available, replace this script with
``prisma db seed`` and insert the same records through the generated client.
"""

from app.db import store


if __name__ == "__main__":
    print("Seeded in-memory demo store")
    print("admin / Admin123!")
    print(f"products: {len(store.products)}")

