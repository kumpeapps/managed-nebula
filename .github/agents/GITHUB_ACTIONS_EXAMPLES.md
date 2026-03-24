# GitHub Actions Integration Examples

This directory contains example workflows showing how to integrate Managed Nebula with your CI/CD pipelines.

## Available Workflow Templates

Copy these to your repository's `.github/workflows/` directory and customize as needed.

### 1. Provision Client on Deployment

**File**: `provision-nebula-client.yml`

```yaml
name: Provision Nebula Client

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment (dev, staging, prod)'
        required: true
        type: choice
        options:
          - dev
          - staging
          - prod
      service_name:
        description: 'Service name'
        required: true
        type: string

jobs:
  provision:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests pyyaml
      
      - name: Provision Nebula Client
        env:
          NEBULA_API_URL: ${{ secrets.NEBULA_API_URL }}
          NEBULA_API_KEY: ${{ secrets.NEBULA_API_KEY }}
          ENVIRONMENT: ${{ inputs.environment }}
          SERVICE_NAME: ${{ inputs.service_name }}
        run: |
          python - <<'EOF'
          import os
          import requests
          import json
          
          api_url = os.getenv('NEBULA_API_URL')
          api_key = os.getenv('NEBULA_API_KEY')
          env = os.getenv('ENVIRONMENT')
          service = os.getenv('SERVICE_NAME')
          
          headers = {
              'Authorization': f'Bearer {api_key}',
              'Content-Type': 'application/json'
          }
          
          # Map environments to group IDs
          groups = {
              'dev': [1],
              'staging': [2],
              'prod': [3]
          }
          
          # Create client
          client_name = f'{env}-{service}'
          payload = {
              'name': client_name,
              'group_ids': groups[env],
              'pool_id': 1
          }
          
          print(f'Creating Nebula client: {client_name}')
          response = requests.post(
              f'{api_url}/api/v1/clients',
              headers=headers,
              json=payload
          )
          response.raise_for_status()
          
          client = response.json()
          print(f'✅ Created client with IP: {client["ip_address"]}')
          print(f'   Token: {client["token"][:20]}...')
          
          # Save token as output
          with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
              f.write(f'client_id={client["id"]}\n')
              f.write(f'client_token={client["token"]}\n')
              f.write(f'client_ip={client["ip_address"]}\n')
          EOF
      
      - name: Store Client Token
        env:
          CLIENT_TOKEN: ${{ steps.provision.outputs.client_token }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # Store as GitHub secret for this environment
          gh secret set NEBULA_CLIENT_TOKEN \
            --body "$CLIENT_TOKEN" \
            --env ${{ inputs.environment }} \
            --repo ${{ github.repository }}
```

### 2. Health Check Workflow

**File**: `nebula-health-check.yml`

```yaml
name: Nebula Network Health Check

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check Network Health
        env:
          NEBULA_API_URL: ${{ secrets.NEBULA_API_URL }}
          NEBULA_API_KEY: ${{ secrets.NEBULA_API_KEY }}
        run: |
          python - <<'EOF'
          import os
          import requests
          import json
          from datetime import datetime, timedelta
          
          api_url = os.getenv('NEBULA_API_URL')
          api_key = os.getenv('NEBULA_API_KEY')
          
          headers = {'Authorization': f'Bearer {api_key}'}
          
          # Get all clients
          response = requests.get(f'{api_url}/api/v1/clients', headers=headers)
          response.raise_for_status()
          clients = response.json()
          
          # Analyze health
          stats = {
              'total': len(clients),
              'active': 0,
              'inactive': 0,
              'blocked': 0,
              'never_connected': 0,
              'stale': 0  # Not seen in >7 days
          }
          
          stale_clients = []
          now = datetime.utcnow()
          
          for client in clients:
              if client['is_blocked']:
                  stats['blocked'] += 1
              elif not client['last_config_download_at']:
                  stats['never_connected'] += 1
              else:
                  last_seen = datetime.fromisoformat(
                      client['last_config_download_at'].replace('Z', '+00:00')
                  )
                  if (now - last_seen) > timedelta(days=7):
                      stats['stale'] += 1
                      stale_clients.append(client['name'])
                  else:
                      stats['active'] += 1
          
          # Print report
          print('🔍 Nebula Network Health Report')
          print('=' * 50)
          print(f'Total Clients: {stats["total"]}')
          print(f'Active (seen in last 7 days): {stats["active"]}')
          print(f'Never Connected: {stats["never_connected"]}')
          print(f'Stale (not seen in >7 days): {stats["stale"]}')
          print(f'Blocked: {stats["blocked"]}')
          
          if stale_clients:
              print('\n⚠️  Stale Clients:')
              for name in stale_clients:
                  print(f'  - {name}')
          
          # Fail if too many issues
          issues = stats['never_connected'] + stats['stale']
          if issues > stats['total'] * 0.2:  # More than 20% issues
              print(f'\n❌ ALERT: {issues} clients have connection issues!')
              exit(1)
          else:
              print('\n✅ Network health is good')
          EOF
      
      - name: Notify on Failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '⚠️ Nebula Network Health Alert',
              body: 'Health check workflow detected issues. Check the workflow run for details.',
              labels: ['alert', 'nebula']
            });
```

### 3. Cleanup Stale Clients

**File**: `cleanup-stale-clients.yml`

```yaml
name: Cleanup Stale Nebula Clients

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:
    inputs:
      dry_run:
        description: 'Dry run (don\'t actually delete)'
        required: false
        type: boolean
        default: true

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Find and Clean Stale Clients
        env:
          NEBULA_API_URL: ${{ secrets.NEBULA_API_URL }}
          NEBULA_API_KEY: ${{ secrets.NEBULA_API_KEY }}
          DRY_RUN: ${{ inputs.dry_run || 'true' }}
        run: |
          python - <<'EOF'
          import os
          import requests
          from datetime import datetime, timedelta
          
          api_url = os.getenv('NEBULA_API_URL')
          api_key = os.getenv('NEBULA_API_KEY')
          dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
          
          headers = {'Authorization': f'Bearer {api_key}'}
          
          # Get all clients
          response = requests.get(f'{api_url}/api/v1/clients', headers=headers)
          clients = response.json()
          
          # Find stale clients (not seen in 30 days)
          stale_threshold = datetime.utcnow() - timedelta(days=30)
          stale_clients = []
          
          for client in clients:
              if not client['last_config_download_at']:
                  # Never connected - if created >30 days ago, mark stale
                  created = datetime.fromisoformat(
                      client['created_at'].replace('Z', '+00:00')
                  )
                  if created < stale_threshold:
                      stale_clients.append(client)
              else:
                  last_seen = datetime.fromisoformat(
                      client['last_config_download_at'].replace('Z', '+00:00')
                  )
                  if last_seen < stale_threshold:
                      stale_clients.append(client)
          
          print(f'Found {len(stale_clients)} stale clients (>30 days inactive)')
          
          if dry_run:
              print('\n🔍 DRY RUN - Would delete:')
              for client in stale_clients:
                  print(f'  - {client["name"]} (ID: {client["id"]})')
          else:
              print('\n🗑️  Deleting stale clients:')
              for client in stale_clients:
                  response = requests.delete(
                      f'{api_url}/api/v1/clients/{client["id"]}',
                      headers=headers
                  )
                  if response.status_code == 200:
                      print(f'  ✅ Deleted {client["name"]}')
                  else:
                      print(f'  ❌ Failed to delete {client["name"]}')
          EOF
```

### 4. Sync Groups from Git

**File**: `sync-nebula-groups.yml`

```yaml
name: Sync Nebula Groups

on:
  push:
    branches: [main]
    paths:
      - 'nebula-groups.yml'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests pyyaml
      
      - name: Sync Groups
        env:
          NEBULA_API_URL: ${{ secrets.NEBULA_API_URL }}
          NEBULA_API_KEY: ${{ secrets.NEBULA_API_KEY }}
        run: |
          python - <<'EOF'
          import os
          import requests
          import yaml
          
          api_url = os.getenv('NEBULA_API_URL')
          api_key = os.getenv('NEBULA_API_KEY')
          headers = {'Authorization': f'Bearer {api_key}'}
          
          # Load desired groups from file
          with open('nebula-groups.yml', 'r') as f:
              desired_groups = yaml.safe_load(f)
          
          # Get existing groups
          response = requests.get(f'{api_url}/api/v1/groups', headers=headers)
          existing_groups = {g['name']: g for g in response.json()}
          
          # Sync groups
          for group in desired_groups['groups']:
              name = group['name']
              
              if name in existing_groups:
                  print(f'✓ Group exists: {name}')
              else:
                  print(f'+ Creating group: {name}')
                  requests.post(
                      f'{api_url}/api/v1/groups',
                      headers=headers,
                      json={'name': name}
                  )
          EOF
```

**Example `nebula-groups.yml`:**

```yaml
groups:
  - name: production
  - name: staging
  - name: development
  - name: databases
  - name: web-servers
  - name: api-services
```

## Required Secrets

Add these to your repository secrets (Settings → Secrets and variables → Actions):

- `NEBULA_API_URL` - Your Managed Nebula server URL (e.g., `https://nebula.example.com`)
- `NEBULA_API_KEY` - API key generated from Profile → API Keys (format: `mnapi_...`)

## Security Best Practices

1. **Use environment-specific secrets**: Separate API keys for dev/staging/prod
2. **Restrict API key permissions**: When scopes are implemented, use minimal permissions
3. **Rotate keys regularly**: Set expiration dates and rotate every 90 days
4. **Monitor usage**: Check API key usage in Profile → API Keys
5. **Use GitHub environments**: Require approval for production deployments

## Debugging Workflows

Enable debug logging:

```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

## Integration with Deployment Workflows

Combine with your existing deployment workflow:

```yaml
name: Deploy Application

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      # ... your build and test steps ...
      
      - name: Provision Nebula Client
        id: nebula
        uses: ./.github/workflows/provision-nebula-client.yml
        with:
          environment: production
          service_name: ${{ github.event.repository.name }}
      
      - name: Deploy with Nebula Token
        env:
          NEBULA_TOKEN: ${{ steps.nebula.outputs.client_token }}
        run: |
          # Use token in your deployment
          kubectl create secret generic nebula-token \
            --from-literal=token=$NEBULA_TOKEN
```

## Need Help?

Use the Managed Nebula Copilot agent:

```
@managed-nebula How do I create a GitHub Actions workflow that [your requirement]?
```

The agent can help you:
- Write custom workflows
- Debug authentication issues
- Implement retry logic
- Handle errors gracefully
- Add monitoring and alerts
