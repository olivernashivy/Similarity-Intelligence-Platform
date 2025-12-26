"""Initialize database with sample data."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import AsyncSessionLocal
from app.models.organization import Organization
from app.auth.api_key import create_api_key


async def init_sample_data():
    """Create sample organization and API key."""
    async with AsyncSessionLocal() as db:
        try:
            # Create sample organization
            org = Organization(
                name="Demo Organization",
                email="demo@example.com",
                tier="starter",
                allow_corpus_inclusion=False,
                store_embeddings=False,
                monthly_check_limit=1000,
                current_month_checks=0,
                is_active=True
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)

            print(f"✓ Created organization: {org.name} ({org.id})")

            # Create API key
            raw_key, api_key = await create_api_key(
                db,
                organization_id=org.id,
                name="Demo API Key",
                rate_limit_per_minute=60
            )

            print(f"✓ Created API key: {api_key.key_prefix}...")
            print(f"\n{'='*60}")
            print(f"SAVE THIS API KEY - IT WON'T BE SHOWN AGAIN:")
            print(f"{'='*60}")
            print(f"\n{raw_key}\n")
            print(f"{'='*60}")
            print(f"\nUse this in the X-API-Key header for API requests.")
            print(f"\nExample:")
            print(f'curl -H "X-API-Key: {raw_key}" http://localhost:8000/v1/usage')

        except Exception as e:
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    print("Initializing database with sample data...")
    asyncio.run(init_sample_data())
