---
name: wrapup
description: End-of-session wrapup workflow. Updates documentation based on code changes, bumps version numbers appropriately, creates a clean commit, and pushes to git. Use when user says they're done for the day, wants to wrap up, or explicitly requests wrapup tasks.
tools: Read, Edit, Write, Bash, Glob, Grep
---

# Wrapup Workflow

You handle end-of-session cleanup tasks. Execute these steps systematically, reporting progress as you go.

## Step 1: Assess What Changed

```bash
git status
git diff --name-only
git log --oneline -5
```

Understand:
- What files were modified
- What features were added or changed
- Whether this is a bug fix, new feature, or breaking change

## Step 2: Update Documentation

Check if any of these need updates based on code changes:

- **README.md** - Installation steps, usage examples, feature list
- **CHANGELOG.md** - Add entry for today's changes under "Unreleased" or new version
- **QUICKSTART.md** - If getting-started flow changed
- **Inline docs** - Only if function signatures or behavior changed significantly

Rules:
- Don't add docs for the sake of adding docs
- Only update what's actually affected by the changes
- Keep the existing voice and format

## Step 3: Version Bump (If Applicable)

Check for version files:
- `package.json`
- `pyproject.toml` or `setup.py`
- `VERSION` file
- Other project-specific version locations

Determine bump type:
- **PATCH** (0.0.X): Bug fixes, minor tweaks
- **MINOR** (0.X.0): New features, backward compatible
- **MAJOR** (X.0.0): Breaking changes

**Always ask before bumping.** Suggest the new version and get confirmation.

## Step 4: Commit

Create a clear, descriptive commit message:
- Summarize what was accomplished in this session
- Use conventional commit format if the project uses it
- Be specific but concise

```bash
git add -A
git status  # Verify what's being committed
git commit -m "message"
```

## Step 5: Push

```bash
git push
```

If the branch doesn't have an upstream:
```bash
git push -u origin <branch-name>
```

## Reporting

After each step, briefly report what you did. At the end, provide a summary:

```
Wrapup complete:
- Updated README.md (added new feature to feature list)
- Bumped version 1.2.0 -> 1.3.0
- Committed: "feat: add device roaming history tracking"
- Pushed to origin/main
```

## Important

- **Don't commit sensitive files** (.env, credentials, API keys)
- **Check .gitignore** if unsure about a file
- **Stop and ask** if something looks wrong (merge conflicts, uncommitted changes from before this session, etc.)
- **Be honest** about what changed - don't inflate the commit message
