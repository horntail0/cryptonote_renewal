# Git Management Skill

## Purpose
This skill defines repository-specific Git workflow rules for `cryptonote_renewal`.
Use this skill whenever a task includes commit, branch, push, PR, or other Git operations.

## Core Rules
- Push target remote must be `origin` with repository URL:
  - `https://github.com/horntail0/cryptonote_renewal.git`
- Default branch is `master`.
- For regular updates, work on `master`.
- For new feature development, create and use a feature branch.
  - Branch naming format: `feature/<name>`
  - Example: `feature/add-simulation-report`

## Branch Policy
1. If the request is a feature addition or behavior expansion:
- Create a branch from `master`:
  - `git checkout master`
  - `git pull origin master`
  - `git checkout -b feature/<name>`
2. If the request is maintenance/fix on current line:
- Use `master` unless the user explicitly asks otherwise.

## Commit/Push Policy
- Commit only intended changes (prefer staged-only commit when requested).
- Do not include unrelated files.
- Push destination:
  - `master` work: `git push -u origin master`
  - feature work: `git push -u origin feature/<name>`

## Failure Analysis Policy
If push fails, report:
1. Exact failing command
2. Error message summary
3. Failure category:
- Network/connectivity
- Authentication/authorization
- Remote protection/policy
- Non-fast-forward/diverged history
- Large file or hook rejection
4. Concrete retry commands

## Reporting Language
- All sub-agent reports to the user must be in Korean by default.

## Extensibility
- This skill is intentionally extendable.
- Add new policy sections as requirements evolve.
