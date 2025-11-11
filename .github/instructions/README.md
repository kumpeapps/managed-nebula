# Copilot Instructions for Managed Nebula

This directory contains scoped instructions for GitHub Copilot coding agent. These instructions help Copilot understand the project's architecture, conventions, and best practices for different parts of the codebase.

## Overview

Managed Nebula uses a comprehensive set of Copilot instructions to provide context-aware AI assistance:

1. **Root instructions** (`.github/copilot-instructions.md`): General architecture and patterns
2. **Scoped instructions** (this directory): Specific guidance for different areas

## Instruction Files

### Core Components

| File | Scope | Purpose |
|------|-------|---------|
| `server.instructions.md` | `server/**/*` | FastAPI backend development, database patterns, API conventions |
| `frontend.instructions.md` | `frontend/**/*`, `**/*.ts` | Angular development, Material UI, RxJS, forms |
| `client.instructions.md` | `client/**/*` | Python agent, certificate management, Docker deployment |

### Development & Operations

| File | Scope | Purpose |
|------|-------|---------|
| `testing.instructions.md` | `**/test_*.py`, `**/*.spec.ts` | Testing patterns for pytest and Jasmine |
| `docker.instructions.md` | `**/Dockerfile`, `**/docker-compose.yml` | Container best practices, troubleshooting |
| `github-actions.instructions.md` | `.github/workflows/**` | CI/CD workflows, multi-arch builds |
| `database-migrations.instructions.md` | `server/alembic/**` | Alembic migration patterns and best practices |

## How It Works

Each instruction file uses YAML frontmatter to define which files it applies to:

```yaml
---
applies_to:
  - server/**/*
  - "**/test_*.py"
---
```

When Copilot is working on a file that matches one of these patterns, it automatically loads the relevant instructions to provide better, context-aware suggestions.

## File Structure

Each instruction file typically includes:

- **Overview**: Brief description of the component/area
- **Tech Stack**: Technologies and frameworks used
- **Development Commands**: How to run, build, test, lint
- **Key Patterns**: Common coding patterns and conventions
- **Best Practices**: DO's and DON'Ts
- **File Structure**: Organization of files and directories
- **Common Pitfalls**: Things to avoid
- **Troubleshooting**: Common issues and solutions
- **Examples**: Code examples demonstrating patterns

## Usage

### For Developers

Simply work on files in the repository. Copilot will automatically:
- Load relevant instructions based on the file you're editing
- Provide suggestions that follow project conventions
- Reference best practices specific to the component

### For Copilot Coding Agent

When assigned a task (via issue, PR comment, or chat):
1. Copilot reads the root instructions (`.github/copilot-instructions.md`)
2. When working on specific files, loads scoped instructions from this directory
3. Applies relevant patterns and conventions in code generation
4. Follows testing, linting, and deployment practices

### Git Workflow

**Important:** Always follow the project's branching strategy:
- Create feature branches from `dev` (not `main`)
- If `dev` doesn't exist, create it from `main` first
- Target all pull requests to `dev` branch
- Only `dev` merges to `main` for releases

See the "Git Workflow and Branching Strategy" section in `.github/copilot-instructions.md` for complete details.

## Maintaining Instructions

### When to Update

Update instructions when:
- Adding new technologies or frameworks
- Changing architectural patterns
- Establishing new conventions
- Discovering common pitfalls
- Adding new build/test/deployment processes

### How to Update

1. Edit the relevant `.instructions.md` file in this directory
2. Use clear, concise language
3. Include examples where helpful
4. Update the `applies_to` pattern if file locations change
5. Commit changes with descriptive message

### Creating New Instructions

To add instructions for a new area:

1. Create `new-area.instructions.md` in this directory
2. Add YAML frontmatter with `applies_to` patterns
3. Follow the structure of existing files
4. Update this README to document the new file

Example:

```markdown
---
applies_to:
  - "docs/**/*"
  - "**/*.md"
---

# Documentation Instructions

## Overview
Guidelines for writing and maintaining documentation...
```

## Coverage

Current instruction coverage:

- ✅ Server (FastAPI backend)
- ✅ Frontend (Angular SPA)
- ✅ Client (Python agent)
- ✅ Testing (pytest, Jasmine)
- ✅ Docker (containers, compose)
- ✅ CI/CD (GitHub Actions)
- ✅ Database Migrations (Alembic)

## Benefits

These instructions help ensure:

- **Consistency**: Code follows established patterns
- **Quality**: Best practices are automatically applied
- **Speed**: Less time explaining context to Copilot
- **Learning**: New contributors learn patterns through suggestions
- **Maintenance**: Reduces technical debt from inconsistent code

## Resources

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [Best Practices for Copilot Coding Agent](https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results)
- [Custom Instructions Announcement](https://github.blog/changelog/2025-07-23-github-copilot-coding-agent-now-supports-instructions-md-custom-instructions/)

## Questions?

For questions about these instructions or suggestions for improvements, please:
- Open an issue in the repository
- Discuss in PR comments
- Contact the maintainers

---

**Last Updated**: 2024-11-11  
**Maintained By**: Managed Nebula Team
