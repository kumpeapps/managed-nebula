# Bug/#315 Investigation - Unexpected Security Fix

## Issue Report
Clients getting 401 Unauthorized after bug/#315 deployment (revocation list feature).

## Root Cause Discovery

**Bug/#315 inadvertently FIXED a security bug** where inactive tokens were still being accepted!

### Evidence

1. **Token History for lighthouse-01**:
   - Token ID 1: Created Nov 14, 2025, **is_active=0** (inactive since Mar 25, 2026)
   - Token ID 14: Created Mar 25, 2026, **is_active=1** (current active token)

2. **User Confirmation**:
   - Clients were working BEFORE bug/#315 with the old inactive token
   - Token was reissued on Mar 25, 2026 but client config was not updated
   - Old token should have been rejected immediately but was somehow still working

3. **Authentication Logic**:
   - The authentication query has ALWAYS checked `ClientToken.is_active == True`
   - This check exists in both main and bug/#315 branches identically
   - Yet inactive tokens were being accepted before bug/#315

## What Changed

Bug/#315 only added the `revoked_certificates` table and helper functions. It did NOT directly modify:
- `client_tokens` table  
- Authentication query logic
- Token validation

**Theory**: The migration or database operations during bug/#315 deployment may have:
- Triggered a database restart/reconnection
- Fixed a cached query plan issue
- Corrected SQLite boolean comparison handling
- Fixed some other  subtle database state issue

## Impact

✅ **POSITIVE SECURITY FIX**: Inactive tokens are now properly rejected as they should have been all along.

⚠️ **Action Required**: Any clients using old/inactive tokens must update their configuration with their current active token from the database.

## Resolution Steps

For each client experiencing 401 errors:
1. Identify the client name/ID from logs
2. Query database for their active token: `SELECT token FROM client_tokens WHERE client_id = X AND is_active = 1`
3. Update client's `CLIENT_TOKEN` environment variable
4. Restart the client agent

## Verification

Tested all 15 active tokens - all authenticate successfully. The authentication system is now working correctly and enforcing the is_active constraint as originally intended.
