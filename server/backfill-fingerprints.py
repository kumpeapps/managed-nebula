#!/usr/bin/env python3
"""
Backfill missing fingerprints for existing certificates.

This script extracts fingerprints from existing certificate PEM data
and updates the database. This is needed for legacy certificates created
before fingerprint extraction was fixed.

Usage:
    python backfill-fingerprints.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_session
from app.services.cert_manager import CertManager


async def main():
    print("Starting fingerprint backfill...")
    print("=" * 60)
    
    async for session in get_session():
        try:
            cert_manager = CertManager(session)
            stats = await cert_manager.backfill_missing_fingerprints()
            
            print("\nBackfill Results:")
            print(f"  Total certificates processed: {stats['total_certificates']}")
            print(f"  Successfully updated: {stats['successfully_updated']}")
            print(f"  Failed: {stats['failed']}")
            
            if stats['errors']:
                print(f"\nErrors encountered:")
                for error in stats['errors'][:10]:  # Show first 10 errors
                    print(f"  - {error}")
                if len(stats['errors']) > 10:
                    print(f"  ... and {len(stats['errors']) - 10} more errors")
            
            print("\n" + "=" * 60)
            if stats['successfully_updated'] > 0:
                print(f"✓ Successfully updated {stats['successfully_updated']} certificates with fingerprints!")
            else:
                print("✗ No certificates were updated. Check errors above.")
            
            break  # Exit after first session
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
