# Auto-Rebase GitHub Bot

Automatically rebases target branches when source branches are updated.

## Features

- ✅ Automatic rebase on push to configured source branches
- ✅ Configurable branch mappings via YAML
- ✅ Conflict detection with automatic issue creation
- ✅ Manual workflow dispatch for ad-hoc rebases
- ✅ Safe force-push using `--force-with-lease`
- ✅ Multi-branch support (one source → many targets)

## Setup

### 1. Configuration File

The bot reads branch mappings from `.github/auto-rebase.yml`:

```yaml
rebase_branches:
  main:
    - dev
  
  develop:
    - feature/experimental
    - staging
```

**Format:**
- **Source branch** (left side): The branch that triggers the rebase
- **Target branch(es)** (right side): Branches to be rebased onto the source
- Supports both single branch (string) or multiple branches (array)

### 2. Workflow Configuration

The workflow is located at `.github/workflows/auto-rebase.yml` and:

- Triggers automatically when source branches receive pushes
- Can be manually triggered via GitHub Actions UI
- Requires `contents: write` and `pull-requests: write` permissions

### 3. Permissions

Ensure the workflow has proper permissions in your repository settings:

**Settings → Actions → General → Workflow permissions**
- ✅ Read and write permissions
- ✅ Allow GitHub Actions to create and approve pull requests

## Usage

### Automatic Rebase

When you push to a configured source branch (e.g., `main`), the workflow automatically:

1. Checks out the repository
2. Reads `.github/auto-rebase.yml` configuration
3. For each target branch:
   - Attempts to rebase onto the source branch
   - Pushes successfully rebased branches
   - Creates an issue if conflicts are detected

### Manual Rebase

You can manually trigger a rebase from the Actions tab:

1. Go to **Actions** → **Auto Rebase Branches**
2. Click **Run workflow**
3. Optionally specify a target branch to override configuration

## Conflict Handling

If a rebase fails due to conflicts:

1. ❌ The rebase is aborted
2. 📋 An issue is created with:
   - Conflict details
   - Manual resolution instructions
   - Link to the failed workflow run
3. 🏷️ Tagged with `auto-rebase-conflict` label

**Manual Resolution:**

```bash
git checkout <target-branch>
git fetch origin
git rebase origin/<source-branch>
# Resolve conflicts in your editor
git add .
git rebase --continue
git push origin <target-branch> --force-with-lease
```

## Example Configuration

### Simple: One source → One target

```yaml
rebase_branches:
  main:
    - dev
```

### Complex: Multiple mappings

```yaml
rebase_branches:
  main:
    - dev
    - staging
  
  release:
    - hotfix
    - production
  
  develop:
    - feature/alpha
    - feature/beta
```

### String format (single target)

```yaml
rebase_branches:
  main: dev
```

## Troubleshooting

### Workflow doesn't trigger

- Verify branch name matches exactly in config file
- Check workflow permissions in repository settings
- Ensure `.github/auto-rebase.yml` exists and is valid YAML

### Rebase always fails

- Check for conflicting changes between branches
- Manually test rebase: `git rebase origin/<source>`
- Review workflow logs in Actions tab

### Issues not created on conflict

- Verify `pull-requests: write` permission is enabled
- Check if `gh` CLI authentication is working
- Issues may already exist (only one per conflict)

## Security

- Uses `--force-with-lease` instead of `--force` to prevent accidental overwrites
- Runs with minimal required permissions
- Only rebases branches explicitly configured
- Creates audit trail via workflow logs

## Customization

### Modify conflict issue template

Edit the `gh issue create` command in `.github/workflows/auto-rebase.yml`:

```yaml
gh issue create \
  --title "Custom title" \
  --body "Custom body" \
  --label "custom-label"
```

### Add notifications

Add a notification step after the rebase:

```yaml
- name: Notify on Slack
  if: success()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {"text": "✅ Auto-rebase completed"}
```

### Change bot identity

Modify the Git configuration:

```yaml
- name: Configure Git
  run: |
    git config user.name "Your Bot Name"
    git config user.email "bot@example.com"
```

## License

This workflow is part of the Managed Nebula project.
