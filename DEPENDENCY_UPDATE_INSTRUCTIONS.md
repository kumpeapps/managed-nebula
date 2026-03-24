# Dependency Update Instructions

This file contains instructions for completing the Dependabot alert resolutions.

## ✅ Python Dependencies (Completed)

The following Python packages have been updated in `requirements.txt` and `server/requirements.txt`:

- **pyasn1**: `0.6.2` → `0.6.3` (Fixes: Denial of Service via Unbounded Recursion)
- **PyJWT**: `2.6.0` → `2.10.1` (Fixes: Accepts unknown `crit` header extensions)

These updates address alerts: #135, #134, #132

## ✅ Angular/Frontend Dependencies (Package.json Updated)

Updated Angular packages in `frontend/package.json` from `21.1.5` to `21.2.0`:
- All Angular packages (@angular/core, @angular/compiler, @angular/common, etc.)
- Angular CLI and dev tools

This addresses XSS vulnerabilities in i18n bindings (alerts: #128, #127, #126, #125, #117, #110)

**Action Required**: Run the following commands to update package-lock.json:

```bash
cd frontend
npm install
npm audit fix
```

This will update package-lock.json with the latest secure versions of:
- flatted (Prototype Pollution fix - #138)
- immutable (Prototype Pollution fix - #116)
- tar (Path Traversal fixes - #121, #118)
- serialize-javascript (RCE fix - #111)
- undici (WebSocket/HTTP issues - #123, #122, #131)
- hono and @hono/node-server (Various fixes - #113, #115, #112, #114, #120)

## ✅ macOS Client Ruby Dependencies (Gemfile Updated)

Updated `macos_client/Gemfile` to specify minimum json version:
- **json**: Added constraint `>= 2.9.1` (Fixes: Format string injection - #137)

**Action Required**: Run the following commands to update Gemfile.lock:

```bash
cd macos_client
bundle update json
```

## Summary

### What was done automatically:
1. ✅ Updated Python packages in requirements.txt files
2. ✅ Updated Angular versions in package.json
3. ✅ Added json version constraint in Gemfile

### What needs to be run manually:
1. ⚠️  `cd frontend && npm install && npm audit fix` - Update npm lockfile
2. ⚠️  `cd macos_client && bundle update json` - Update Ruby lockfile

### Expected Results:
After running the manual steps, all 23 Dependabot alerts should be resolved:
- 18 High severity alerts
- 5 Moderate severity alerts

### Verification:
After completing the manual steps, verify by:
1. Running tests: `cd server && source venv/bin/activate && pytest -q`
2. Checking Dependabot: GitHub Security tab should show 0 open alerts
3. Building frontend: `cd frontend && npm run build`
