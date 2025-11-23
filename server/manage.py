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
from app.models.user import User
from app.models.client import Client, Group, ClientToken, IPAssignment, IPPool, IPGroup, FirewallRuleset, FirewallRule, client_groups, client_firewall_rulesets, ruleset_rules
from app.models.permissions import UserGroup, UserGroupMembership, ClientPermission, Permission, user_group_permissions
from app.models.ca import CACertificate
from app.models.settings import GlobalSettings
from app.core.auth import hash_password
from app.services.cert_manager import CertManager
from app.services.ip_allocator import allocate_ip_from_pool
from sqlalchemy import select, func
from datetime import datetime, timedelta
import secrets
import string


async def bootstrap_permissions(session):
    """Ensure all necessary RBAC permissions exist in the database."""
    permissions_data = [
        # Clients permissions
        ('clients', 'read', 'View client information'),
        ('clients', 'create', 'Create new clients'),
        ('clients', 'update', 'Update client settings'),
        ('clients', 'delete', 'Delete clients'),
        ('clients', 'download', 'Download client configurations'),
        
        # Groups permissions (Nebula groups, not user groups)
        ('groups', 'read', 'View Nebula groups'),
        ('groups', 'create', 'Create new Nebula groups'),
        ('groups', 'update', 'Update Nebula groups'),
        ('groups', 'delete', 'Delete Nebula groups'),
        
        # Firewall rules permissions
        ('firewall_rules', 'read', 'View firewall rules'),
        ('firewall_rules', 'create', 'Create firewall rules'),
        ('firewall_rules', 'update', 'Update firewall rules'),
        ('firewall_rules', 'delete', 'Delete firewall rules'),
        
        # IP pools permissions
        ('ip_pools', 'read', 'View IP pools'),
        ('ip_pools', 'create', 'Create IP pools'),
        ('ip_pools', 'update', 'Update IP pools'),
        ('ip_pools', 'delete', 'Delete IP pools'),
        
        # IP groups permissions
        ('ip_groups', 'read', 'View IP groups'),
        ('ip_groups', 'create', 'Create IP groups'),
        ('ip_groups', 'update', 'Update IP groups'),
        ('ip_groups', 'delete', 'Delete IP groups'),
        
        # CA permissions
        ('ca', 'read', 'View certificate authorities'),
        ('ca', 'create', 'Create certificate authorities'),
        ('ca', 'update', 'Update certificate authority settings'),
        ('ca', 'delete', 'Delete certificate authorities'),
        ('ca', 'download', 'Download CA certificates'),
        
        # Users permissions
        ('users', 'read', 'View users'),
        ('users', 'create', 'Create new users'),
        ('users', 'update', 'Update user settings'),
        ('users', 'delete', 'Delete users'),
        
        # User Groups permissions
        ('user_groups', 'read', 'View user groups'),
        ('user_groups', 'create', 'Create user groups'),
        ('user_groups', 'update', 'Update user groups'),
        ('user_groups', 'delete', 'Delete user groups'),
        ('user_groups', 'manage_members', 'Add/remove members from user groups'),
        
        # Settings permissions
        ('settings', 'read', 'View system settings'),
        ('settings', 'update', 'Update system settings'),
        ('settings', 'docker_compose', 'Download docker-compose configurations'),
        
        # Lighthouse permissions
        ('lighthouse', 'read', 'View lighthouse settings'),
        ('lighthouse', 'update', 'Update lighthouse settings'),
        
        # Dashboard permissions
        ('dashboard', 'read', 'View dashboard and statistics'),
    ]
    
    created_count = 0
    for resource, action, description in permissions_data:
        # Check if permission exists
        existing = (await session.execute(
            select(Permission).where(
                Permission.resource == resource,
                Permission.action == action
            )
        )).scalars().first()
        
        if not existing:
            permission = Permission(
                resource=resource,
                action=action,
                description=description
            )
            session.add(permission)
            created_count += 1
    
    if created_count > 0:
        await session.flush()
    
    return created_count


async def create_admin_user(email: str, password: str):
    """Create an admin user and add to Administrators group."""
    async with AsyncSessionLocal() as session:
        # Bootstrap permissions first
        perm_count = await bootstrap_permissions(session)
        if perm_count > 0:
            print(f"🔐 Created {perm_count} missing permissions")
        
        # Check if user already exists
        existing = (await session.execute(
            select(User).where(User.email == email)
        )).scalars().first()
        
        if existing:
            print(f"❌ User with email '{email}' already exists!")
            return False
        
        # Create user
        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=True
        )
        session.add(user)
        await session.flush()

        # Ensure Administrators group exists
        admins = (await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))).scalars().first()
        if not admins:
            admins = UserGroup(name="Administrators", description="Administrators with full access", is_admin=True)
            session.add(admins)
            await session.flush()

        # Add user to Administrators group (required for admin access)
        session.add(UserGroupMembership(user_id=user.id, user_group_id=admins.id))

        await session.commit()
        
        print(f"✅ Admin user created successfully: {email}")
        print(f"✅ User added to Administrators group for admin access")
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
    """List all users with group memberships."""
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
            # Load groups
            groups = (await session.execute(
                select(UserGroup).join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
                .where(UserGroupMembership.user_id == user.id)
            )).scalars().all()
            group_names = ", ".join(g.name for g in groups) if groups else "(none)"
            status = "✅ active" if user.is_active else "❌ inactive"
            print(f"  {user.email:<40} | groups: {group_names:<25} | {status}")
        print("-" * 80)


async def make_admin(email: str):
    """Make an existing user an admin: add to Administrators group."""
    async with AsyncSessionLocal() as session:
        # Bootstrap permissions first
        perm_count = await bootstrap_permissions(session)
        if perm_count > 0:
            print(f"🔐 Created {perm_count} missing permissions")
        
        user = (await session.execute(
            select(User).where(User.email == email)
        )).scalars().first()
        
        if not user:
            print(f"❌ User with email '{email}' not found!")
            return False

        # Ensure Administrators group exists
        admins = (await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))).scalars().first()
        if not admins:
            admins = UserGroup(name="Administrators", description="Administrators with full access", is_admin=True)
            session.add(admins)
            await session.flush()
        
        # Add membership if missing
        existing = (await session.execute(
            select(UserGroupMembership).where(UserGroupMembership.user_id == user.id, UserGroupMembership.user_group_id == admins.id)
        )).scalars().first()
        
        if existing:
            print(f"ℹ️  User '{email}' is already an admin (member of Administrators group)")
            return True
        
        session.add(UserGroupMembership(user_id=user.id, user_group_id=admins.id))
        await session.commit()
        
        print(f"✅ User '{email}' is now an admin!")
        print(f"✅ Added to Administrators group")
        return True


async def create_demo_data():
    """Create comprehensive demo data for testing and showcasing the platform."""
    async with AsyncSessionLocal() as session:
        print("🌌 Creating demo data for Managed Nebula...")
        print("=" * 60)
        
        # Bootstrap permissions first
        print("🔐 Bootstrapping RBAC permissions...")
        perm_count = await bootstrap_permissions(session)
        if perm_count > 0:
            print(f"  ✅ Created {perm_count} missing permissions")
        else:
            print(f"  ℹ️  All permissions already exist")
        await session.commit()
        
        # Check if demo data already exists
        existing_clients = (await session.execute(select(func.count(Client.id)))).scalar()
        if existing_clients > 0:
            print("⚠️  Demo data may already exist. Continuing anyway...")
        
        # 1. Create demo users
        print("\n👥 Creating demo users...")
        
        # Ensure Administrators group exists
        admins_group = (await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))).scalars().first()
        if not admins_group:
            admins_group = UserGroup(name="Administrators", description="Administrators with full access", is_admin=True)
            session.add(admins_group)
            await session.flush()
        
        # Create demo users if they don't exist
        demo_users = [
            ("admin@demo.com", "admin123", True, "Demo Admin"),
            ("alice@demo.com", "alice123", False, "Alice Johnson"),
            ("bob@demo.com", "bob123", False, "Bob Smith"),
            ("charlie@demo.com", "charlie123", False, "Charlie Brown"),
        ]
        
        created_users = {}
        for email, password, is_admin, name in demo_users:
            existing = (await session.execute(select(User).where(User.email == email))).scalars().first()
            if not existing:
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    is_active=True
                )
                session.add(user)
                await session.flush()
                created_users[email] = user
                
                # Add admin user to Administrators group
                if is_admin:
                    session.add(UserGroupMembership(user_id=user.id, user_group_id=admins_group.id))
                
                print(f"  ✅ Created user: {email} (password: {password}{'  [admin]' if is_admin else ''})")
            else:
                created_users[email] = existing
                print(f"  ℹ️  User exists: {email}")
        
        # 2. Create user groups
        print("\n👥 Creating user groups...")
        
        user_groups_data = [
            ("Developers", "Development team members", created_users["admin@demo.com"]),
            ("Operations", "Operations and DevOps team", created_users["alice@demo.com"]),
            ("QA Team", "Quality assurance engineers", created_users["bob@demo.com"]),
        ]
        
        created_user_groups = {}
        for name, description, owner in user_groups_data:
            existing = (await session.execute(select(UserGroup).where(UserGroup.name == name))).scalars().first()
            if not existing:
                user_group = UserGroup(
                    name=name,
                    description=description,
                    owner_user_id=owner.id
                )
                session.add(user_group)
                await session.flush()
                created_user_groups[name] = user_group
                print(f"  ✅ Created user group: {name}")
            else:
                created_user_groups[name] = existing
                print(f"  ℹ️  User group exists: {name}")
        
        # Add members to user groups
        memberships = [
            ("Developers", [created_users["alice@demo.com"], created_users["bob@demo.com"]]),
            ("Operations", [created_users["alice@demo.com"], created_users["charlie@demo.com"]]),
            ("QA Team", [created_users["bob@demo.com"], created_users["charlie@demo.com"]]),
        ]
        
        for group_name, members in memberships:
            group = created_user_groups[group_name]
            for member in members:
                existing = (await session.execute(
                    select(UserGroupMembership).where(
                        UserGroupMembership.user_group_id == group.id,
                        UserGroupMembership.user_id == member.id
                    )
                )).scalars().first()
                
                if not existing:
                    membership = UserGroupMembership(
                        user_group_id=group.id,
                        user_id=member.id
                    )
                    session.add(membership)
        
        # Grant permissions to user groups
        print("\n🔐 Granting permissions to user groups...")
        
        # Get all read permissions for standard user groups
        read_permissions = (await session.execute(
            select(Permission).where(Permission.action == 'read')
        )).scalars().all()
        
        # Grant read permissions to all non-admin user groups
        for group_name, group in created_user_groups.items():
            if not group.is_admin:  # Only grant to non-admin groups
                for perm in read_permissions:
                    # Check if permission already granted
                    existing = (await session.execute(
                        select(user_group_permissions).where(
                            user_group_permissions.c.user_group_id == group.id,
                            user_group_permissions.c.permission_id == perm.id
                        )
                    )).first()
                    
                    if not existing:
                        await session.execute(
                            user_group_permissions.insert().values(
                                user_group_id=group.id,
                                permission_id=perm.id
                            )
                        )
                
                print(f"  ✅ Granted read permissions to {group_name}")
        
        # Grant additional permissions for specific groups
        # Developers get create/update permissions for clients and groups
        dev_perms = (await session.execute(
            select(Permission).where(
                ((Permission.resource == 'clients') & (Permission.action.in_(['create', 'update', 'download']))) |
                ((Permission.resource == 'groups') & (Permission.action.in_(['create', 'update']))) |
                ((Permission.resource == 'firewall_rules') & (Permission.action == 'read'))
            )
        )).scalars().all()
        
        if 'Developers' in created_user_groups:
            dev_group = created_user_groups['Developers']
            for perm in dev_perms:
                existing = (await session.execute(
                    select(user_group_permissions).where(
                        user_group_permissions.c.user_group_id == dev_group.id,
                        user_group_permissions.c.permission_id == perm.id
                    )
                )).first()
                
                if not existing:
                    await session.execute(
                        user_group_permissions.insert().values(
                            user_group_id=dev_group.id,
                            permission_id=perm.id
                        )
                    )
            print(f"  ✅ Granted additional permissions to Developers (create/update clients & groups)")
        
        # Operations get full permissions for IP pools, IP groups, and settings
        ops_perms = (await session.execute(
            select(Permission).where(
                (Permission.resource.in_(['ip_pools', 'ip_groups', 'settings', 'lighthouse'])) |
                ((Permission.resource == 'clients') & (Permission.action.in_(['update', 'download'])))
            )
        )).scalars().all()
        
        if 'Operations' in created_user_groups:
            ops_group = created_user_groups['Operations']
            for perm in ops_perms:
                existing = (await session.execute(
                    select(user_group_permissions).where(
                        user_group_permissions.c.user_group_id == ops_group.id,
                        user_group_permissions.c.permission_id == perm.id
                    )
                )).first()
                
                if not existing:
                    await session.execute(
                        user_group_permissions.insert().values(
                            user_group_id=ops_group.id,
                            permission_id=perm.id
                        )
                    )
            print(f"  ✅ Granted additional permissions to Operations (manage IPs & settings)")
        
        await session.commit()
        
        # 3. Ensure global settings exist
        print("\n⚙️  Setting up global settings...")
        settings = (await session.execute(select(GlobalSettings))).scalars().first()
        if not settings:
            settings = GlobalSettings(
                punchy_enabled=True,
                client_docker_image="ghcr.io/kumpeapps/managed-nebula/client:latest",
                server_url="https://localhost:4200"
            )
            session.add(settings)
            print("  ✅ Created global settings")
        else:
            print("  ℹ️  Global settings exist")
        
        # 4. Create Certificate Authority
        print("\n🔐 Creating Certificate Authority...")
        existing_ca = (await session.execute(select(CACertificate).where(CACertificate.is_active == True))).scalars().first()
        if not existing_ca:
            cert_manager = CertManager(session)
            ca = await cert_manager.create_new_ca("Demo-CA")
            print("  ✅ Created demo Certificate Authority")
        else:
            print("  ℹ️  Certificate Authority exists")
        
        # 5. Create IP pools and groups
        print("\n🌐 Creating IP pools and groups...")
        
        # Main pool
        main_pool = (await session.execute(select(IPPool).where(IPPool.cidr == "10.100.0.0/16"))).scalars().first()
        if not main_pool:
            main_pool = IPPool(
                cidr="10.100.0.0/16",
                description="Main network pool for all clients"
            )
            session.add(main_pool)
            await session.flush()
            print("  ✅ Created main IP pool: 10.100.0.0/16")
        else:
            print("  ℹ️  Main IP pool exists")
        
        # DMZ pool
        dmz_pool = (await session.execute(select(IPPool).where(IPPool.cidr == "10.200.0.0/24"))).scalars().first()
        if not dmz_pool:
            dmz_pool = IPPool(
                cidr="10.200.0.0/24", 
                description="DMZ network for servers and services"
            )
            session.add(dmz_pool)
            await session.flush()
            print("  ✅ Created DMZ IP pool: 10.200.0.0/24")
        else:
            print("  ℹ️  DMZ IP pool exists")
        
        # Create IP groups
        ip_groups_data = [
            (main_pool.id, "Developers", "10.100.1.1", "10.100.1.50", "IP range for development team"),
            (main_pool.id, "Operations", "10.100.2.1", "10.100.2.50", "IP range for operations team"),
            (main_pool.id, "QA", "10.100.3.1", "10.100.3.30", "IP range for QA team"),
            (dmz_pool.id, "Servers", "10.200.0.10", "10.200.0.50", "Server IP range"),
        ]
        
        created_ip_groups = {}
        for pool_id, name, start_ip, end_ip, description in ip_groups_data:
            existing = (await session.execute(
                select(IPGroup).where(IPGroup.name == name, IPGroup.pool_id == pool_id)
            )).scalars().first()
            
            if not existing:
                ip_group = IPGroup(
                    pool_id=pool_id,
                    name=name,
                    start_ip=start_ip,
                    end_ip=end_ip
                )
                session.add(ip_group)
                await session.flush()
                created_ip_groups[name] = ip_group
                print(f"  ✅ Created IP group: {name} ({start_ip}-{end_ip})")
            else:
                created_ip_groups[name] = existing
                print(f"  ℹ️  IP group exists: {name}")
        
        # 6. Create Nebula groups
        print("\n🏷️  Creating Nebula groups...")
        
        groups_data = [
            ("developers", "Development team with code access"),
            ("operations", "Operations team with infrastructure access"),
            ("qa", "QA team with testing environment access"),
            ("servers", "Production servers and services"),
            ("lighthouses", "Lighthouse nodes for network discovery"),
            ("database", "Database servers"),
            ("web", "Web servers and applications"),
        ]
        
        created_groups = {}
        for name, description in groups_data:
            existing = (await session.execute(select(Group).where(Group.name == name))).scalars().first()
            if not existing:
                group = Group(
                    name=name,
                    owner_user_id=created_users["admin@demo.com"].id
                )
                session.add(group)
                await session.flush()
                created_groups[name] = group
                print(f"  ✅ Created group: {name}")
            else:
                created_groups[name] = existing
                print(f"  ℹ️  Group exists: {name}")
        
        # 7. Create firewall rulesets
        print("\n🔥 Creating firewall rulesets...")
        
        # Web server ruleset
        web_ruleset_name = "Web Server Access"
        existing_web = (await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name == web_ruleset_name)
        )).scalars().first()
        
        if not existing_web:
            web_ruleset = FirewallRuleset(
                name=web_ruleset_name,
                description="Allow HTTP/HTTPS traffic to web servers"
            )
            session.add(web_ruleset)
            await session.flush()
            
            # Add rules to web ruleset
            web_rules = [
                ("inbound", "80", "tcp", None, "0.0.0.0/0", None, None, None),
                ("inbound", "443", "tcp", None, "0.0.0.0/0", None, None, None),
                ("outbound", "any", "any", None, "0.0.0.0/0", None, None, None),
            ]
            
            # Create rules and associate them via direct database insert
            rule_ids = []
            for direction, port, proto, host, cidr, local_cidr, ca_name, ca_sha in web_rules:
                rule = FirewallRule(
                    direction=direction,
                    port=port,
                    proto=proto,
                    host=host,
                    cidr=cidr,
                    local_cidr=local_cidr,
                    ca_name=ca_name,
                    ca_sha=ca_sha
                )
                session.add(rule)
                await session.flush()
                rule_ids.append(rule.id)
            
            # Associate rules with ruleset
            from app.models.client import ruleset_rules
            for rule_id in rule_ids:
                await session.execute(
                    ruleset_rules.insert().values(ruleset_id=web_ruleset.id, rule_id=rule_id)
                )
            
            print(f"  ✅ Created ruleset: {web_ruleset_name}")
        
        # Database server ruleset
        db_ruleset_name = "Database Server Access"
        existing_db = (await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name == db_ruleset_name)
        )).scalars().first()
        
        if not existing_db:
            db_ruleset = FirewallRuleset(
                name=db_ruleset_name,
                description="Database access for application servers"
            )
            session.add(db_ruleset)
            await session.flush()
            
            # Add rules to database ruleset
            db_rules = [
                ("inbound", "5432", "tcp", None, "10.100.0.0/16", None, None, None),  # PostgreSQL
                ("inbound", "3306", "tcp", None, "10.100.0.0/16", None, None, None),  # MySQL
                ("inbound", "6379", "tcp", None, "10.100.0.0/16", None, None, None),  # Redis
            ]
            
            # Create rules and associate them via direct database insert
            rule_ids = []
            for direction, port, proto, host, cidr, local_cidr, ca_name, ca_sha in db_rules:
                rule = FirewallRule(
                    direction=direction,
                    port=port,
                    proto=proto,
                    host=host,
                    cidr=cidr,
                    local_cidr=local_cidr,
                    ca_name=ca_name,
                    ca_sha=ca_sha
                )
                session.add(rule)
                await session.flush()
                rule_ids.append(rule.id)
            
            # Associate rules with ruleset
            for rule_id in rule_ids:
                await session.execute(
                    ruleset_rules.insert().values(ruleset_id=db_ruleset.id, rule_id=rule_id)
                )
            
            print(f"  ✅ Created ruleset: {db_ruleset_name}")
        
        # Developer access ruleset
        dev_ruleset_name = "Developer Access"
        existing_dev = (await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name == dev_ruleset_name)
        )).scalars().first()
        
        if not existing_dev:
            dev_ruleset = FirewallRuleset(
                name=dev_ruleset_name,
                description="Development tools and SSH access"
            )
            session.add(dev_ruleset)
            await session.flush()
            
            # Add rules to dev ruleset
            dev_rules = [
                ("inbound", "22", "tcp", None, "10.100.1.0/24", None, None, None),   # SSH from dev IPs
                ("inbound", "3000", "tcp", None, "10.100.0.0/16", None, None, None), # Dev server
                ("inbound", "8080", "tcp", None, "10.100.0.0/16", None, None, None), # Alt dev port
                ("outbound", "any", "any", None, "0.0.0.0/0", None, None, None),     # Outbound access
            ]
            
            # Create rules and associate them via direct database insert
            rule_ids = []
            for direction, port, proto, host, cidr, local_cidr, ca_name, ca_sha in dev_rules:
                rule = FirewallRule(
                    direction=direction,
                    port=port,
                    proto=proto,
                    host=host,
                    cidr=cidr,
                    local_cidr=local_cidr,
                    ca_name=ca_name,
                    ca_sha=ca_sha
                )
                session.add(rule)
                await session.flush()
                rule_ids.append(rule.id)
            
            # Associate rules with ruleset
            for rule_id in rule_ids:
                await session.execute(
                    ruleset_rules.insert().values(ruleset_id=dev_ruleset.id, rule_id=rule_id)
                )
            
            print(f"  ✅ Created ruleset: {dev_ruleset_name}")
        
        await session.commit()
        
        # Refresh objects after commit to get IDs
        web_ruleset = (await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name == web_ruleset_name)
        )).scalars().first()
        db_ruleset = (await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name == db_ruleset_name)
        )).scalars().first()
        dev_ruleset = (await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name == dev_ruleset_name)
        )).scalars().first()
        
        # 8. Create demo clients
        print("\n💻 Creating demo clients...")
        
        def generate_token():
            return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        clients_data = [
            # Lighthouses
            ("lighthouse-01", True, "203.0.113.10", False, ["lighthouses"], [], main_pool, None),
            ("lighthouse-02", True, "203.0.113.11", False, ["lighthouses"], [], main_pool, None),
            
            # Web servers
            ("web-server-01", False, None, False, ["web", "servers"], [web_ruleset], dmz_pool, "Servers"),
            ("web-server-02", False, None, False, ["web", "servers"], [web_ruleset], dmz_pool, "Servers"),
            
            # Database servers
            ("db-primary", False, None, False, ["database", "servers"], [db_ruleset], dmz_pool, "Servers"),
            ("db-replica", False, None, False, ["database", "servers"], [db_ruleset], dmz_pool, "Servers"),
            
            # Developer machines
            ("alice-laptop", False, None, False, ["developers"], [dev_ruleset], main_pool, "Developers"),
            ("bob-workstation", False, None, False, ["developers", "qa"], [dev_ruleset], main_pool, "Developers"),
            
            # Operations
            ("ops-server", False, None, False, ["operations", "servers"], [dev_ruleset], main_pool, "Operations"),
            ("monitoring", False, None, False, ["operations"], [], main_pool, "Operations"),
            
            # QA environment
            ("qa-test-01", False, None, False, ["qa"], [], main_pool, "QA"),
            ("qa-test-02", False, None, False, ["qa"], [], main_pool, "QA"),
        ]
        
        created_clients = {}
        for name, is_lighthouse, public_ip, is_blocked, group_names, rulesets, pool, ip_group_name in clients_data:
            existing = (await session.execute(select(Client).where(Client.name == name))).scalars().first()
            if not existing:
                # Create client
                client = Client(
                    name=name,
                    is_lighthouse=is_lighthouse,
                    public_ip=public_ip,
                    is_blocked=is_blocked,
                    owner_user_id=created_users["admin@demo.com"].id,
                    config_last_changed_at=datetime.utcnow()
                )
                session.add(client)
                await session.flush()
                
                # Allocate IP
                ip_group = created_ip_groups[ip_group_name] if ip_group_name else None
                if ip_group:
                    from app.services.ip_allocator import allocate_ip_from_group
                    allocated_ip = await allocate_ip_from_group(session, pool, ip_group)
                else:
                    from app.services.ip_allocator import allocate_ip_from_pool
                    allocated_ip = await allocate_ip_from_pool(session, pool)
                
                # Create IP assignment
                assignment = IPAssignment(
                    ip_address=allocated_ip,
                    client_id=client.id,
                    pool_id=pool.id,
                    ip_group_id=ip_group.id if ip_group else None
                )
                session.add(assignment)
                
                # Create token
                token = ClientToken(
                    client_id=client.id,
                    token=generate_token(),
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(token)
                
                await session.flush()
                
                # Add to groups using association table
                for group_name in group_names:
                    if group_name in created_groups:
                        await session.execute(
                            client_groups.insert().values(
                                client_id=client.id, 
                                group_id=created_groups[group_name].id
                            )
                        )
                
                # Add firewall rulesets using association table
                for ruleset in rulesets:
                    if ruleset:
                        await session.execute(
                            client_firewall_rulesets.insert().values(
                                client_id=client.id,
                                firewall_ruleset_id=ruleset.id
                            )
                        )
                
                created_clients[name] = client
                print(f"  ✅ Created client: {name} ({allocated_ip if allocated_ip else 'no IP'})")
            else:
                created_clients[name] = existing
                print(f"  ℹ️  Client exists: {name}")
        
        # 9. Create client permissions for demo users
        print("\n🔑 Setting up client permissions...")
        
        permissions_data = [
            # Alice (operations) gets access to operations and server clients
            (created_users["alice@demo.com"], ["ops-server", "monitoring", "web-server-01", "db-primary"], 
             {"can_view": True, "can_update": True, "can_download_config": True}),
            
            # Bob (developer/QA) gets access to dev and QA clients
            (created_users["bob@demo.com"], ["alice-laptop", "bob-workstation", "qa-test-01", "qa-test-02"],
             {"can_view": True, "can_update": False, "can_download_config": True}),
            
            # Charlie gets limited access to QA
            (created_users["charlie@demo.com"], ["qa-test-01", "qa-test-02"],
             {"can_view": True, "can_update": False, "can_download_config": False}),
        ]
        
        for user, client_names, permissions in permissions_data:
            for client_name in client_names:
                if client_name in created_clients:
                    client = created_clients[client_name]
                    
                    # Check if permission already exists
                    existing = (await session.execute(
                        select(ClientPermission).where(
                            ClientPermission.client_id == client.id,
                            ClientPermission.user_id == user.id
                        )
                    )).scalars().first()
                    
                    if not existing:
                        permission = ClientPermission(
                            client_id=client.id,
                            user_id=user.id,
                            **permissions
                        )
                        session.add(permission)
                        print(f"  ✅ Granted {user.email} access to {client_name}")
        
        await session.commit()
        
        print("\n" + "=" * 60)
        print("🎉 Demo data creation completed successfully!")
        print("\nDemo accounts created:")
        print("  👤 admin@demo.com / admin123 (Admin)")
        print("  👤 alice@demo.com / alice123 (User - Operations)")
        print("  👤 bob@demo.com / bob123 (User - Developer/QA)")
        print("  👤 charlie@demo.com / charlie123 (User - QA)")
        print("\nDemo environment includes:")
        print(f"  📊 {len(created_clients)} demo clients")
        print(f"  🏷️  {len(created_groups)} Nebula groups")
        print(f"  👥 {len(created_user_groups)} user groups")
        print(f"  🔥 3 firewall rulesets")
        print(f"  🌐 2 IP pools with IP groups")
        print("  🔐 Certificate Authority")
        print("\nYou can now explore the platform with realistic demo data!")
        print("Access the web interface and login with any of the demo accounts.")


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
  
  seed-demo                          Create comprehensive demo data for testing
                                     (users, clients, groups, firewall rules, etc.)

Examples:
  python manage.py create-admin admin@example.com
  python manage.py create-admin admin@example.com MySecurePass123
  python manage.py reset-password user@example.com
  python manage.py make-admin user@example.com
  python manage.py list-users
  python manage.py seed-demo

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
    
    elif command == "seed-demo":
        print("⚠️  This will create demo data in your database.")
        print("   It's safe to run on a fresh install or existing database.")
        confirm = input("Continue? (y/N): ").lower().strip()
        if confirm in ['y', 'yes']:
            asyncio.run(create_demo_data())
        else:
            print("❌ Demo data creation cancelled.")
    
    else:
        print(f"❌ Error: Unknown command '{command}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
