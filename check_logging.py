#!/usr/bin/env python3
"""Enable debug logging to see actual request bodies causing 401 errors."""
import sys
import os
sys.path.insert(0, "/app")
os.chdir("/app")

# Read main.py to check logging level
with open("/app/app/main.py", "r") as f:
    content = f.read()
    if "DEBUG" in content:
        print("✓ Debug logging appears to be configured")
    else:
        print("✗ Debug logging not found in main.py")
    
    # Check for middleware that might log request bodies
    if "RequestResponseLoggerMiddleware" in content or "log_request_body" in content:
        print("✓ Request logging middleware found")
    else:
        print("⚠ No request body logging middleware found")

print("\nTo debug 401 errors, we need to see the actual token values being sent.")
print("Suggestion: Add temporary logging in the get_client_config endpoint:")
print("  logger.debug(f'Token validation attempt: {body.token[:12]}... (length: {len(body.token)})')")
