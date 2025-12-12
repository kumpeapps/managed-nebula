#!/bin/bash
set -e

echo "=== Git Branch Cleanup Script ==="
echo ""

# Determine the default branch (main or master)
echo "🔍 Detecting default branch..."
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

if ! git show-ref --verify --quiet refs/heads/$DEFAULT_BRANCH; then
  # Try the other common name
  if [ "$DEFAULT_BRANCH" = "main" ]; then
    DEFAULT_BRANCH="master"
  else
    DEFAULT_BRANCH="main"
  fi
fi

echo "  Default branch: $DEFAULT_BRANCH"
echo ""

# Switch to default branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" ]; then
  echo "🔄 Switching to $DEFAULT_BRANCH branch..."
  git checkout $DEFAULT_BRANCH
  echo ""
fi

# Fetch with prune to remove remote-tracking branches that no longer exist
echo "📡 Fetching from remote and pruning deleted branches..."
git fetch --prune

echo ""
echo "🔍 Finding local branches that don't exist on remote..."
echo ""

# Find branches in two categories:
# 1. Branches without upstream tracking
# 2. Branches whose upstream no longer exists on remote

BRANCHES_NO_UPSTREAM=$(git for-each-ref --format '%(refname:short) %(upstream:short)' refs/heads | \
  awk '$2 == "" {print $1}' | \
  grep -v "^${DEFAULT_BRANCH}$" | \
  grep -v "^main$" | \
  grep -v "^master$" | \
  grep -v "^dev$" || true)

BRANCHES_GONE_UPSTREAM=$(git for-each-ref --format '%(refname:short) %(upstream:track)' refs/heads | \
  awk '$2 == "[gone]" {print $1}' || true)

# Combine and deduplicate
BRANCHES_TO_DELETE=$(echo -e "${BRANCHES_NO_UPSTREAM}\n${BRANCHES_GONE_UPSTREAM}" | sort -u | grep -v '^$' || true)

if [ -z "$BRANCHES_TO_DELETE" ]; then
  echo "✅ No orphaned local branches found. All local branches have remotes."
  exit 0
fi

echo "Found the following local branches without remotes:"
echo "$BRANCHES_TO_DELETE" | while read branch; do
  echo "  - $branch"
done

echo ""
read -p "Delete these branches? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo "🗑️  Deleting branches..."
  echo "$BRANCHES_TO_DELETE" | while read branch; do
    if [ "$branch" != "$DEFAULT_BRANCH" ] && [ "$branch" != "main" ] && [ "$branch" != "master" ]; then
      echo "  Deleting: $branch"
      git branch -D "$branch" 2>&1 | sed 's/^/    /'
    fi
  done
  echo ""
  echo "✅ Cleanup complete!"
  echo ""
  echo "📥 Pulling latest changes from $DEFAULT_BRANCH..."
  git pull
  echo ""
  echo "🎉 All done!"
else
  echo ""
  echo "❌ Cleanup cancelled."
  exit 1
fi
