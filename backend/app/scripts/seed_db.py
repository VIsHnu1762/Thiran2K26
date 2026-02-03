"""
BillAgent Pro - Database Seeding
=================================
Script to seed the database with initial data.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.database import async_engine, AsyncSessionLocal, Base
from backend.app.models import GLCode, Vendor, User, UserRole
from backend.app.models.gl_code import DEFAULT_GL_CODES
from backend.app.services.auth_service import hash_password


async def seed_gl_codes(session) -> int:
    """Seed default GL codes."""
    from sqlalchemy import select
    
    created = 0
    for code_data in DEFAULT_GL_CODES:
        # Check if exists
        result = await session.execute(
            select(GLCode).where(GLCode.code == code_data["code"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            gl_code = GLCode(**code_data)
            session.add(gl_code)
            created += 1
            print(f"  ✅ Created GL Code: {code_data['code']} - {code_data['name']}")
        else:
            print(f"  ⏭️  GL Code exists: {code_data['code']}")
    
    if created > 0:
        await session.commit()
    
    return created


async def seed_sample_vendors(session) -> int:
    """Seed sample vendors for testing."""
    from sqlalchemy import select
    
    sample_vendors = [
        {
            "name": "Office Supplies Co.",
            "default_gl_code": "5100",
            "email": "billing@officesupplies.com",
            "phone": "+91 98765 43210"
        },
        {
            "name": "Tech Solutions Ltd.",
            "default_gl_code": "5400",
            "email": "accounts@techsolutions.in",
            "phone": "+91 98765 43211"
        },
        {
            "name": "Cloud Services India",
            "default_gl_code": "5400",
            "email": "invoices@cloudservices.in",
            "phone": "+91 98765 43212"
        },
        {
            "name": "Professional Services Group",
            "default_gl_code": "5500",
            "email": "billing@proservices.com",
            "phone": "+91 98765 43213"
        },
        {
            "name": "Marketing Agency Pro",
            "default_gl_code": "5600",
            "email": "finance@marketingpro.com",
            "phone": "+91 98765 43214"
        },
    ]
    
    created = 0
    for vendor_data in sample_vendors:
        # Check if exists
        result = await session.execute(
            select(Vendor).where(Vendor.name == vendor_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            vendor = Vendor(**vendor_data)
            session.add(vendor)
            created += 1
            print(f"  ✅ Created Vendor: {vendor_data['name']}")
        else:
            print(f"  ⏭️  Vendor exists: {vendor_data['name']}")
    
    if created > 0:
        await session.commit()
    
    return created


async def seed_demo_users(session) -> int:
    """Seed demo users for testing authentication."""
    from sqlalchemy import select
    
    demo_users = [
        {
            "email": "admin@billagent.pro",
            "password": "admin123456",
            "full_name": "Admin User",
            "role": UserRole.ADMIN,
            "is_superuser": True
        },
        {
            "email": "approver@billagent.pro",
            "password": "approver123456",
            "full_name": "Bill Approver",
            "role": UserRole.APPROVER,
            "is_superuser": False
        },
        {
            "email": "accountant@billagent.pro",
            "password": "account123456",
            "full_name": "Accountant User",
            "role": UserRole.ACCOUNTANT,
            "is_superuser": False
        },
        {
            "email": "viewer@billagent.pro",
            "password": "viewer123456",
            "full_name": "Viewer User",
            "role": UserRole.VIEWER,
            "is_superuser": False
        },
    ]
    
    created = 0
    for user_data in demo_users:
        # Check if exists
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_superuser=user_data["is_superuser"],
                is_active=True
            )
            session.add(user)
            created += 1
            print(f"  ✅ Created User: {user_data['email']} ({user_data['role'].value})")
        else:
            print(f"  ⏭️  User exists: {user_data['email']}")
    
    if created > 0:
        await session.commit()
    
    return created


async def main():
    """Run all seeders."""
    print("\n" + "=" * 60)
    print("BillAgent Pro - Database Seeder")
    print("=" * 60 + "\n")
    
    async with AsyncSessionLocal() as session:
        # Seed GL Codes
        print("📋 Seeding GL Codes...")
        gl_count = await seed_gl_codes(session)
        print(f"   Created {gl_count} GL codes\n")
        
        # Seed Sample Vendors
        print("🏢 Seeding Sample Vendors...")
        vendor_count = await seed_sample_vendors(session)
        print(f"   Created {vendor_count} vendors\n")
        
        # Seed Demo Users
        print("👤 Seeding Demo Users...")
        user_count = await seed_demo_users(session)
        print(f"   Created {user_count} users\n")
    
    print("=" * 60)
    print("✅ Seeding complete!")
    print("=" * 60 + "\n")
    
    # Print demo credentials
    print("\n📝 Demo Credentials:")
    print("-" * 40)
    print("Admin:      admin@billagent.pro / admin123456")
    print("Approver:   approver@billagent.pro / approver123456")
    print("Accountant: accountant@billagent.pro / account123456")
    print("Viewer:     viewer@billagent.pro / viewer123456")
    print("-" * 40 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
