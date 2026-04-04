---
description: Git version control guidelines and commit message conventions for mtg-utils
author: Simone Gasbarroni
version: 1.0
tags: ["git", "version-control", "workflow"]
---

# Version Control

## Git Workflow

This document outlines the version control practices for the mtg-utils project.

---

## Branching Strategy

### Branch Types

- `main` - Production-ready code
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates

### Naming Conventions

```bash
# Feature branch
feature/add-new-command

# Fix branch
fix/resolve-api-error

# Documentation branch
docs/update-readme
```

---

## Commit Message Conventions

### Format

```
<type>: <subject>

<body>
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Maintenance tasks

### Examples

```bash
feat: add check-missing-cards command
fix: resolve API timeout issue
docs: update README with installation instructions
test: add unit tests for card library
```

---

## Pull Request Guidelines

### Before Submitting PR

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] PR title follows conventional commit format

### PR Description Template

```
## Description
Brief description of changes

## Type of Change
- [ ] Feature
- [ ] Fix
- [ ] Documentation
- [ ] Test
- [ ] Refactor

## Testing
Describe how you tested the changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added where necessary
```

---

## Gitignore Patterns

The following files are ignored:

- `.env` - Environment variables
- `config.json` - User configuration
- `card_library/` - Generated data directory
- `venv/` - Python virtual environment
- `__pycache__/` - Python cache

---

## Versioning

Version numbers follow Semantic Versioning (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes (backward compatible)
