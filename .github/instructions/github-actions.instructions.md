---
applies_to:
  - ".github/workflows/**"
  - "**/.github/workflows/*.yml"
  - "**/.github/workflows/*.yaml"
---

# GitHub Actions CI/CD Instructions

## Overview
Managed Nebula uses GitHub Actions for continuous integration and deployment. Workflows build and push Docker images to Harbor registry for multi-architecture support (amd64/arm64).

## Existing Workflows

### Image Build and Push Workflows
- **push-server.yml**: Builds and pushes server (FastAPI backend) image
- **push-frontend.yml**: Builds and pushes frontend (Angular) image
- **push-client.yml**: Builds and pushes client (Python agent) image

Each workflow:
- Triggers on push to `dev`, `main` branches or version tags (`v*`)
- Builds multi-architecture images (linux/amd64, linux/arm64)
- Pushes to Harbor registry at `harbor.vm.kumpeapps.com`
- Uses layer caching for faster builds
- Tags appropriately based on branch/tag

## Key Patterns

### Trigger Conditions
```yaml
on:
  push:
    branches: [ dev, main ]
    tags: [ 'v*' ]
    paths:
      - 'server/**'          # Only trigger when relevant files change
      - '.github/workflows/push-server.yml'
  workflow_dispatch:         # Allow manual trigger
```

### Concurrency Control
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true   # Cancel old builds when new one starts
```

### Multi-Architecture Builds
```yaml
- name: Set up QEMU (multi-arch emulation)
  uses: docker/setup-qemu-action@v3

- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build and Push
  run: |
    docker buildx build --push \
      --platform linux/amd64,linux/arm64 \
      --tag harbor.vm.kumpeapps.com/managed-nebula/server:latest \
      ./server
```

### Registry Authentication
```yaml
- name: Login to Harbor (with retry)
  run: |
    for i in 1 2 3; do
      echo "${{ secrets.HARBOR_SECRET }}" | docker login harbor.vm.kumpeapps.com -u "robot_github" --password-stdin && exit 0
      echo "Login failed (attempt $i), retrying in 5s...";
      sleep 5;
    done
    echo "Failed to login to Harbor after 3 attempts" >&2
    exit 1
```

### Build Caching
```yaml
docker buildx build --push \
  --cache-from type=gha,scope=server-main \
  --cache-to type=gha,mode=max,scope=server-main \
  --cache-from type=registry,ref=harbor.vm.kumpeapps.com/managed-nebula/server:latest \
  --platform linux/amd64,linux/arm64 ./server
```

### Conditional Tagging
```yaml
# Development builds (dev branch)
- name: Build and Push Image (dev-latest)
  if: github.ref == 'refs/heads/dev'
  run: docker buildx build --push --tag harbor.vm.kumpeapps.com/managed-nebula/server:dev-latest ./server

# Production builds (main branch)
- name: Build and Push Image (latest)
  if: github.ref == 'refs/heads/main'
  run: docker buildx build --push --tag harbor.vm.kumpeapps.com/managed-nebula/server:latest ./server

# Release builds (version tags)
- name: Build and Push Image (tag)
  if: startsWith(github.ref, 'refs/tags/')
  run: |
    TAG=${GITHUB_REF#refs/tags/}
    docker buildx build --push --tag harbor.vm.kumpeapps.com/managed-nebula/server:$TAG ./server
```

## Best Practices

### DO's ✅
- **Use specific action versions**: Pin to major version (e.g., `@v4`, not `@latest`)
- **Use concurrency control**: Prevent resource waste from parallel builds
- **Set timeouts**: Prevent hung builds from consuming minutes
- **Cache layers**: Use GitHub Actions cache and registry cache
- **Path filters**: Only trigger on relevant file changes
- **Retry transient failures**: Network operations should retry
- **Use secrets for credentials**: Never hardcode passwords
- **Multi-architecture builds**: Support both amd64 and arm64
- **Conditional steps**: Skip unnecessary steps based on context

### DON'Ts ❌
- ❌ Don't use `latest` action versions - pin to specific versions
- ❌ Don't hardcode secrets in workflow files
- ❌ Don't run workflows on every file change - use path filters
- ❌ Don't forget timeouts - prevent infinite hangs
- ❌ Don't skip build caching - wastes time and resources
- ❌ Don't build for unused platforms - only amd64/arm64 needed
- ❌ Don't push to `latest` from feature branches
- ❌ Don't forget `--provenance=false` flag (avoids attestation issues)

## Common Workflow Patterns

### Testing Before Build
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd server
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd server
          pytest tests/ -v

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      # Build steps...
```

### Matrix Strategy for Multiple Versions
```yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      # Test steps...
```

### Artifact Upload/Download
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Build frontend
        run: npm run build:prod
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v3
        with:
          name: dist
          path: dist/
```

### Pull Request Checks
```yaml
on:
  pull_request:
    branches: [ main, dev ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint code
        run: npm run lint
  
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test
```

## Security Considerations

### Secrets Management
- **HARBOR_SECRET**: Harbor registry password (stored in repository secrets)
- Never log secret values
- Use `${{ secrets.NAME }}` syntax
- Rotate secrets regularly
- Use least privilege service accounts

### Branch Protection
```yaml
# Only allow builds from protected branches
- name: Check branch
  if: github.ref != 'refs/heads/main' && github.ref != 'refs/heads/dev'
  run: |
    echo "Builds only allowed from main or dev branches"
    exit 1
```

### Image Signing (Future Enhancement)
```yaml
- name: Sign image
  uses: sigstore/cosign-installer@v3
- name: Sign the published Docker image
  run: cosign sign harbor.vm.kumpeapps.com/managed-nebula/server:latest
```

## Troubleshooting

### Build Failures

**Registry connection issues:**
```yaml
# Add preflight check
- name: Preflight - Harbor DNS and TLS reachability
  run: |
    set -x
    getent hosts harbor.vm.kumpeapps.com || true
    nslookup harbor.vm.kumpeapps.com || true
    curl -vkI --max-time 15 https://harbor.vm.kumpeapps.com/v2/ || true
```

**Docker timeout issues:**
```yaml
env:
  DOCKER_CLIENT_TIMEOUT: 300
  COMPOSE_HTTP_TIMEOUT: 300
```

**Buildx driver issues:**
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
  with:
    driver-opts: |
      image=moby/buildkit:latest
      network=host
```

**Cache issues:**
```bash
# Clear GitHub Actions cache manually from UI
# Or use different cache scope:
--cache-from type=gha,scope=server-new
```

### Debugging Workflows

**Enable debug logging:**
```bash
# Set repository secrets:
ACTIONS_RUNNER_DEBUG=true
ACTIONS_STEP_DEBUG=true
```

**Local testing with act:**
```bash
# Install act: https://github.com/nektos/act
brew install act

# Run workflow locally
act push -j build-and-push-server
```

**View workflow runs:**
- GitHub UI: Actions tab → select workflow → view run
- Check logs for each step
- Download logs for offline analysis

## Performance Optimization

### Reduce Build Time
- Use layer caching (GitHub Actions cache + registry cache)
- Optimize Dockerfile layer order
- Use multi-stage builds
- Parallelize independent jobs
- Use path filters to skip unnecessary builds

### Reduce Minutes Usage
- Set appropriate timeouts
- Cancel in-progress runs
- Skip duplicate builds with concurrency control
- Use self-hosted runners for high-frequency builds (if needed)

## Adding New Workflows

### Workflow Checklist
- [ ] Add descriptive name
- [ ] Set appropriate triggers (push/pull_request/workflow_dispatch)
- [ ] Add path filters if applicable
- [ ] Use concurrency control
- [ ] Set timeout for all jobs
- [ ] Pin action versions
- [ ] Use secrets for credentials
- [ ] Add error handling
- [ ] Test workflow on feature branch first
- [ ] Document new workflow in this file

### Example: Add Dependency Scanning
```yaml
name: Dependency Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: './server'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

## Registry Configuration

### Current Setup
- **Registry**: Harbor at `harbor.vm.kumpeapps.com`
- **Authentication**: Robot account `robot_github`
- **Credential**: Stored in `HARBOR_SECRET` repository secret
- **Images**: 
  - `harbor.vm.kumpeapps.com/managed-nebula/server`
  - `harbor.vm.kumpeapps.com/managed-nebula/frontend`
  - `harbor.vm.kumpeapps.com/managed-nebula/client`

### Alternative Registries
If switching to GitHub Container Registry (ghcr.io):

```yaml
- name: Login to GitHub Container Registry
  uses: docker/login-action@v2
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and Push
  run: |
    docker buildx build --push \
      --tag ghcr.io/${{ github.repository }}/server:latest \
      ./server
```

## Monitoring and Alerts

### Workflow Status Badge
```markdown
![Build Status](https://github.com/kumpeapps/managed-nebula/actions/workflows/push-server.yml/badge.svg)
```

### Email Notifications
Configure in repository settings → Notifications

### Slack/Discord Integration
```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "Build failed: ${{ github.workflow }} on ${{ github.ref }}"
      }
```

## Resources
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx Documentation](https://docs.docker.com/build/buildx/)
- [Harbor Documentation](https://goharbor.io/docs/)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/security-hardening-for-github-actions)
