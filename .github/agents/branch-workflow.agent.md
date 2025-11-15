---
name: branch-workflow
description: Enforce branching policy (branch from dev; regex ^(feature|bugfix|hotfix|docs|refactor)/(server|frontend|client|all)-[0-9]+$), PRs target dev, title prefix [branch]; prefer scripts/branch-agent.sh; workflow-only.
target: github-copilot
tools: ["read", "search", "edit", "shell"]
---
