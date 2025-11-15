#!/usr/bin/env bash
set -euo pipefail

REMOTE="origin"
DEV_BRANCH="dev"
MAIN_BRANCH="main"

# Allow both manual branches and Copilot-generated branches
branch_regex='^((feature|bugfix|hotfix|docs|refactor)/(server|frontend|client|all)-[0-9]+|copilot/.*)$'

usage() {
  cat <<'USAGE'
Branch Agent - managed-nebula

Commands:
  ensure-dev                    Ensure remote dev branch exists from main
  create-branch TYPE SERVICE ISSUE [DESC]
                                Create feature branch from dev following naming rules
  check                         Validate current branch naming and policy
  pr-title [DESCRIPTION]        Print PR title in required format
  rebase-dev                    Rebase current branch on latest origin/dev

Examples:
  ./scripts/branch-agent.sh ensure-dev
  ./scripts/branch-agent.sh create-branch feature server 5 "Add auth endpoint"
  ./scripts/branch-agent.sh check
  ./scripts/branch-agent.sh pr-title "Add auth endpoint"
  ./scripts/branch-agent.sh rebase-dev
USAGE
}

ensure_dev() {
  git fetch --all --prune
  if git ls-remote --exit-code "$REMOTE" "refs/heads/$DEV_BRANCH" >/dev/null 2>&1; then
    echo "Remote $DEV_BRANCH already exists."
    return 0
  fi

  echo "Creating $DEV_BRANCH from $MAIN_BRANCH and pushing to $REMOTE..."
  # Prefer remote main if available
  if git ls-remote --exit-code "$REMOTE" "refs/heads/$MAIN_BRANCH" >/dev/null 2>&1; then
    git checkout -B "$DEV_BRANCH" "$REMOTE/$MAIN_BRANCH"
  else
    git checkout -B "$DEV_BRANCH" "$MAIN_BRANCH"
  fi
  git push -u "$REMOTE" "$DEV_BRANCH"
  echo "Created and pushed $DEV_BRANCH."
}

create_branch() {
  if [[ $# -lt 3 ]]; then
    echo "Usage: create-branch TYPE SERVICE ISSUE [DESC]" >&2
    exit 2
  fi
  local type="$1" service="$2" issue="$3"; shift 3 || true
  local desc="${*:-}"
  local name="${type}/${service}-${issue}"

  if [[ ! $name =~ $branch_regex ]]; then
    echo "Error: branch must match pattern: $branch_regex" >&2
    exit 1
  fi

  ensure_dev
  git fetch "$REMOTE" "$DEV_BRANCH"
  git checkout -B "$name" "$REMOTE/$DEV_BRANCH"
  git push -u "$REMOTE" "$name" || true

  if [[ -n "$desc" ]]; then
    echo "Suggested PR title: [${name}] ${desc}"
  else
    echo "Branch created: ${name}"
    echo "Tip: ./scripts/branch-agent.sh pr-title 'Short description'"
  fi
}

check_branch() {
  local cur
  cur=$(git rev-parse --abbrev-ref HEAD)
  if [[ "$cur" == "$MAIN_BRANCH" ]]; then
    echo "Error: Do not develop on $MAIN_BRANCH. Use $DEV_BRANCH and feature branches." >&2
    exit 1
  fi
  if [[ "$cur" == "$DEV_BRANCH" ]]; then
    echo "On $DEV_BRANCH. Create a feature branch before committing changes."
    return 0
  fi
  if [[ ! $cur =~ $branch_regex ]]; then
    echo "Error: Current branch '$cur' does not match required pattern: $branch_regex" >&2
    echo "Use: TYPE one of {feature,bugfix,hotfix,docs,refactor}; SERVICE one of {server,frontend,client,all}; ISSUE numeric." >&2
    echo "Or use Copilot-generated branch names starting with 'copilot/'." >&2
    exit 1
  fi
  echo "Branch '$cur' looks good."
}

pr_title() {
  local cur desc
  cur=$(git rev-parse --abbrev-ref HEAD)
  if [[ ! $cur =~ $branch_regex ]]; then
    echo "Error: Current branch '$cur' does not match required pattern; cannot format PR title." >&2
    exit 1
  fi
  desc="${*:-Short description here}"
  echo "[${cur}] ${desc}"
}

rebase_dev() {
  ensure_dev
  local cur
  cur=$(git rev-parse --abbrev-ref HEAD)
  if [[ "$cur" == "$DEV_BRANCH" ]]; then
    echo "Already on $DEV_BRANCH; fast-forwarding from origin..."
    git pull --ff-only "$REMOTE" "$DEV_BRANCH"
  else
    echo "Rebasing '$cur' onto $REMOTE/$DEV_BRANCH..."
    git fetch "$REMOTE" "$DEV_BRANCH"
    git rebase "$REMOTE/$DEV_BRANCH"
  fi
  echo "Rebase complete."
}

cmd="${1:-}"
case "$cmd" in
  ensure-dev) shift; ensure_dev "$@" ;;
  create-branch) shift; create_branch "$@" ;;
  check) shift; check_branch "$@" ;;
  pr-title) shift; pr_title "$@" ;;
  rebase-dev) shift; rebase_dev "$@" ;;
  -h|--help|help|"") usage ;;
  *) echo "Unknown command: $cmd" >&2; usage; exit 2 ;;
esac
