"""
Seed script to populate database with test data.

Usage:
    python scripts/seed_test_data.py

Creates:
    - 2 organizations (free and pro tier)
    - 5 users (admin, members, viewers)
    - 3 API keys
    - Sample check data

Environment Variables:
    DATABASE_URL - Database connection string
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.organization import Organization
from app.models.user import User
from app.models.api_key import APIKey
from app.auth.jwt import get_password_hash
from app.auth.api_key import hash_api_key
import secrets


async def seed_data():
    """Seed database with test data."""
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False
    )

    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        print("🌱 Seeding test data...")

        # Check if data already exists
        result = await session.execute(select(Organization))
        existing = result.scalars().first()
        if existing:
            print("⚠️  Database already contains data. Skipping seed.")
            print("💡 To reseed, drop the database and run migrations first.")
            return

        # ===== ORGANIZATION 1: Free Tier =====
        print("\n📦 Creating Organization 1 (Free Tier)...")
        org1 = Organization(
            name="Acme News Corp",
            email="contact@acmenews.com",
            tier="free",
            monthly_check_limit=100,
            allow_corpus_inclusion=False,
            store_embeddings=False,
            current_month_checks=15
        )
        session.add(org1)
        await session.flush()

        # Users for Org 1
        print("  👤 Creating users for Acme News Corp...")
        user1_admin = User(
            organization_id=org1.id,
            email="admin@acmenews.com",
            username="acme_admin",
            hashed_password=get_password_hash("admin123!"),
            full_name="Alice Admin",
            role="admin",
            is_active=True,
            email_verified=True,
            last_login_at=datetime.utcnow() - timedelta(hours=2)
        )
        session.add(user1_admin)

        user1_member = User(
            organization_id=org1.id,
            email="editor@acmenews.com",
            username="acme_editor",
            hashed_password=get_password_hash("editor123!"),
            full_name="Bob Editor",
            role="member",
            is_active=True,
            email_verified=True,
            last_login_at=datetime.utcnow() - timedelta(days=1)
        )
        session.add(user1_member)

        # API Key for Org 1
        print("  🔑 Creating API key for Acme News Corp...")
        api_key1_value = f"sk_live_{secrets.token_urlsafe(32)}"
        api_key1 = APIKey(
            organization_id=org1.id,
            name="Production API Key",
            key_hash=hash_api_key(api_key1_value),
            key_prefix=api_key1_value[:12],
            rate_limit_per_minute=60,
            is_active=True,
            last_used_at=datetime.utcnow() - timedelta(hours=1),
            total_requests=145
        )
        session.add(api_key1)

        # ===== ORGANIZATION 2: Pro Tier =====
        print("\n📦 Creating Organization 2 (Pro Tier)...")
        org2 = Organization(
            name="TechInsight Media",
            email="contact@techinsight.io",
            tier="pro",
            monthly_check_limit=1000,
            allow_corpus_inclusion=True,
            store_embeddings=True,
            current_month_checks=342
        )
        session.add(org2)
        await session.flush()

        # Users for Org 2
        print("  👤 Creating users for TechInsight Media...")
        user2_admin = User(
            organization_id=org2.id,
            email="cto@techinsight.io",
            username="tech_cto",
            hashed_password=get_password_hash("cto123!"),
            full_name="Carol CTO",
            role="admin",
            is_active=True,
            email_verified=True,
            last_login_at=datetime.utcnow()
        )
        session.add(user2_admin)

        user2_member1 = User(
            organization_id=org2.id,
            email="researcher@techinsight.io",
            username="tech_researcher",
            hashed_password=get_password_hash("research123!"),
            full_name="David Researcher",
            role="member",
            is_active=True,
            email_verified=True,
            last_login_at=datetime.utcnow() - timedelta(hours=3)
        )
        session.add(user2_member1)

        user2_viewer = User(
            organization_id=org2.id,
            email="intern@techinsight.io",
            username="tech_intern",
            hashed_password=get_password_hash("intern123!"),
            full_name="Eve Intern",
            role="viewer",
            is_active=True,
            email_verified=False,
            last_login_at=datetime.utcnow() - timedelta(days=2)
        )
        session.add(user2_viewer)

        # API Keys for Org 2
        print("  🔑 Creating API keys for TechInsight Media...")
        api_key2_prod_value = f"sk_live_{secrets.token_urlsafe(32)}"
        api_key2_prod = APIKey(
            organization_id=org2.id,
            name="Production Key",
            key_hash=hash_api_key(api_key2_prod_value),
            key_prefix=api_key2_prod_value[:12],
            rate_limit_per_minute=100,
            is_active=True,
            last_used_at=datetime.utcnow(),
            total_requests=3542
        )
        session.add(api_key2_prod)

        api_key2_dev_value = f"sk_live_{secrets.token_urlsafe(32)}"
        api_key2_dev = APIKey(
            organization_id=org2.id,
            name="Development Key",
            key_hash=hash_api_key(api_key2_dev_value),
            key_prefix=api_key2_dev_value[:12],
            rate_limit_per_minute=60,
            is_active=True,
            last_used_at=datetime.utcnow() - timedelta(hours=12),
            total_requests=856
        )
        session.add(api_key2_dev)

        # ===== SUPERUSER =====
        print("\n👑 Creating superuser...")
        superuser = User(
            organization_id=org1.id,  # Belongs to org1 but has superuser flag
            email="superuser@platform.com",
            username="superuser",
            hashed_password=get_password_hash("super123!"),
            full_name="Super User",
            role="admin",
            is_active=True,
            is_superuser=True,
            email_verified=True,
            last_login_at=datetime.utcnow()
        )
        session.add(superuser)

        # Commit all
        await session.commit()

        print("\n✅ Test data seeded successfully!")
        print("\n" + "="*60)
        print("📋 TEST ACCOUNTS")
        print("="*60)

        print("\n🏢 ORGANIZATION 1: Acme News Corp (Free Tier)")
        print("  Email: contact@acmenews.com")
        print("  Limit: 100 checks/month | Used: 15")
        print("\n  👤 Users:")
        print(f"     Admin:  admin@acmenews.com / admin123!")
        print(f"     Member: editor@acmenews.com / editor123!")
        print(f"\n  🔑 API Key:")
        print(f"     {api_key1_value}")

        print("\n🏢 ORGANIZATION 2: TechInsight Media (Pro Tier)")
        print("  Email: contact@techinsight.io")
        print("  Limit: 1000 checks/month | Used: 342")
        print("\n  👤 Users:")
        print(f"     Admin:  cto@techinsight.io / cto123!")
        print(f"     Member: researcher@techinsight.io / research123!")
        print(f"     Viewer: intern@techinsight.io / intern123!")
        print(f"\n  🔑 API Keys:")
        print(f"     Production: {api_key2_prod_value}")
        print(f"     Development: {api_key2_dev_value}")

        print("\n👑 SUPERUSER:")
        print(f"   Email: superuser@platform.com / super123!")

        print("\n" + "="*60)
        print("📝 USAGE EXAMPLES")
        print("="*60)

        print("\n1️⃣  Login as Admin:")
        print("""
curl -X POST http://localhost:8000/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@acmenews.com",
    "password": "admin123!"
  }'
""")

        print("2️⃣  Use API Key for Similarity Check:")
        print(f"""
curl -X POST http://localhost:8000/v1/check \\
  -H "X-API-Key: {api_key1_value}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "article_text": "Your article content here...",
    "sources": ["articles", "youtube"],
    "sensitivity": "medium"
  }}'
""")

        print("3️⃣  Get Organization Info (with JWT):")
        print("""
curl -X GET http://localhost:8000/v1/organizations/current \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
""")

        print("\n💡 TIP: Visit http://localhost:8000/docs for interactive API documentation")
        print("="*60)

    await engine.dispose()


if __name__ == "__main__":
    print("🚀 Starting seed script...")
    print(f"📊 Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'localhost'}")
    print("")

    try:
        asyncio.run(seed_data())
    except KeyboardInterrupt:
        print("\n\n⚠️  Seed interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
