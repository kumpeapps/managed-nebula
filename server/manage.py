#!/usr/bin/env python3
"""
Management CLI for Managed Nebula
Provides commands for administrative tasks like creating users, resetting passwords, etc.
"""
import asyncio
import sys
import os
from getpass import getpass

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db import AsyncSessionLocal
from app.models.user import User, Role
from app.core.auth import hash_password
from sqlalchemy import select


async def create_admin_user(email: str, password: str):
    """Create an admin user."""
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        existing = (await session.execute(
            select(User).where(User.email == email)
        )).scalars().first()
        
        if existing:
            print(f"❌ User with email '{email}' already exists!")
            return False
        
        # Ensure admin role exists
        admin_role = (await session.execute(
            select(Role).where(Role.name == "admin")
        )).scalars().first()
        
        if not admin_role:
            print("Creating admin role...")
            admin_role = Role(name="admin")
            session.add(admin_role)
            await session.flush()
        
        # Create user
        user = User(
            email=email,
            hashed_password=hash_password(password),
            role_id=admin_role.id,
            is_active=True
        )
        session.add(user)
        await session.commit()
        
        print(f"✅ Admin user created successfully: {email}")
        return True


async def reset_password(email: str, new_password: str):
    """Reset a user's password."""
    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.email == email)
        )).scalars().first()
        
        if not user:
            print(f"❌ User with email '{email}' not found!")
            return False
        
        user.hashed_password = hash_password(new_password)
        await session.commit()
        
        print(f"✅ Password reset successfully for: {email}")
        return True


async def list_users():
    """List all users."""
    async with AsyncSessionLocal() as session:
        users = (await session.execute(
            select(User).order_by(User.created_at)
        )).scalars().all()
        
        if not users:
            print("No users found in database.")
            return
        
        print("\n📋 Users:")
        print("-" * 80)
        for user in users:
            # Eager load role
            role = (await session.execute(
                select(Role).where(Role.id == user.role_id)
            )).scalars().first()
            role_name = role.name if role else "none"
            status = "✅ active" if user.is_active else "❌ inactive"
            print(f"  {user.email:<40} | {role_name:<10} | {status}")
        print("-" * 80)


async def make_admin(email: str):
    """Make an existing user an admin."""
    async with AsyncSessionLocal() as session:
        user = (await session.execute(
            select(User).where(User.email == email)
        )).scalars().first()
        
        if not user:
            print(f"❌ User with email '{email}' not found!")
            return False
        
        # Ensure admin role exists
        admin_role = (await session.execute(
            select(Role).where(Role.name == "admin")
        )).scalars().first()
        
        if not admin_role:
            print("Creating admin role...")
            admin_role = Role(name="admin")
            session.add(admin_role)
            await session.flush()
        
        user.role_id = admin_role.id
        await session.commit()
        
        print(f"✅ User '{email}' is now an admin!")
        return True


def print_usage():
    """Print usage information."""
    print("""
🌌 Managed Nebula - Management CLI

Usage: python manage.py <command> [options]

Commands:
  create-admin <email> [password]   Create a new admin user
                                     If password is omitted, you'll be prompted
  
  reset-password <email> [password] Reset a user's password
                                     If password is omitted, you'll be prompted
  
  make-admin <email>                 Grant admin role to existing user
  
  list-users                         List all users in the database

Examples:
  python manage.py create-admin admin@example.com
  python manage.py create-admin admin@example.com MySecurePass123
  python manage.py reset-password user@example.com
  python manage.py make-admin user@example.com
  python manage.py list-users

Environment Variables:
  DB_URL         Database connection string (default: sqlite+aiosqlite:///./app.db)
  SECRET_KEY     Application secret key (required for password hashing)
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "create-admin":
        if len(sys.argv) < 3:
            print("❌ Error: Email is required")
            print("Usage: python manage.py create-admin <email> [password]")
            sys.exit(1)
        
        email = sys.argv[2]
        
        if len(sys.argv) >= 4:
            password = sys.argv[3]
        else:
            password = getpass("Enter password: ")
            password_confirm = getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Error: Passwords do not match!")
                sys.exit(1)
        
        if not password:
            print("❌ Error: Password cannot be empty!")
            sys.exit(1)
        
        asyncio.run(create_admin_user(email, password))
    
    elif command == "reset-password":
        if len(sys.argv) < 3:
            print("❌ Error: Email is required")
            print("Usage: python manage.py reset-password <email> [password]")
            sys.exit(1)
        
        email = sys.argv[2]
        
        if len(sys.argv) >= 4:
            password = sys.argv[3]
        else:
            password = getpass("Enter new password: ")
            password_confirm = getpass("Confirm new password: ")
            if password != password_confirm:
                print("❌ Error: Passwords do not match!")
                sys.exit(1)
        
        if not password:
            print("❌ Error: Password cannot be empty!")
            sys.exit(1)
        
        asyncio.run(reset_password(email, password))
    
    elif command == "make-admin":
        if len(sys.argv) < 3:
            print("❌ Error: Email is required")
            print("Usage: python manage.py make-admin <email>")
            sys.exit(1)
        
        email = sys.argv[2]
        asyncio.run(make_admin(email))
    
    elif command == "list-users":
        asyncio.run(list_users())
    
    else:
        print(f"❌ Error: Unknown command '{command}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
