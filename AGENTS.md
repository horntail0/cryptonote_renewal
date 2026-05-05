# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python-based crypto portfolio/trade analysis workspace.

- Core orchestration: `main.py`
- Wallet/domain models: `CoinWallet.py`, `CoinAsset.py`
- Exchange adapters: `Binance_Reader.py`, `Bithumb_Reader.py`, `Gateio_Reader.py`, `GateioV2API.py`, `Reader.py`
- Utility/history scripts: `HistoryManager.py`, `renamefiles.py`
- Ad-hoc test scripts: `main_test.py`, `main_test_2.py`
- Data artifacts: `assets.xlsx`, `history/`, `history_backup*/`, `*.json`

Keep exchange-specific logic inside each `*_Reader.py` file; keep cross-exchange aggregation in `main.py` and wallet/model files.

## Build, Test, and Development Commands
Use PowerShell in the repository root.

- `python -m venv .venv` then `.venv\Scripts\Activate.ps1`: create and activate local environment
- `pip install -r requirements.txt`: install dependencies if a requirements file is present
- `python main.py`: run the main aggregation/export workflow
- `python main_test.py` / `python main_test_2.py`: run script-style validation flows
- `python -m py_compile *.py`: quick syntax check across top-level modules

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and preserve existing module naming like `Binance_Reader.py`.
- Keep functions focused and exchange-agnostic where possible.
- Load secrets from `.env` via `python-dotenv`; do not hardcode API keys.

## Testing Guidelines
- Current tests are script-based, not a formal test framework.
- For new logic, prefer adding focused executable checks near existing patterns (for example, extend `main_test.py`).
- Name future automated tests clearly by behavior (example: `test_merge_coinasset_dicts.py`) if a test framework is introduced.
- Before submitting changes, run affected scripts and confirm no regression in asset merge/export behavior.

## Commit & Pull Request Guidelines
Git metadata is not available in this directory (`.git` missing), so adopt this convention:

- Commit message format: `type(scope): summary` (example: `fix(reader): handle empty trade history`)
- Keep commits small and single-purpose.
- PRs should include: purpose, changed files, run commands, and sample output/screenshots for report or Excel changes.
- Reference related issue/task IDs when available.

## Git Agent Operation Rule
- For any Git-related request (status/branch/commit/push/pull/rebase/PR), always use a dedicated Git sub-agent.
- The Git sub-agent must report to the user in Korean by default.
- Before executing Git work, always check and follow:
  - `skills/git-management/SKILL.md`
- This skill is the source of truth for repository-specific Git workflow.
- If skill content is updated, the latest version must be applied immediately.

## UI Agent Operation Rule
- For any UI-related request, always use the dedicated UI sub-agent first.
- `app.py` modification is owned by the UI sub-agent.
- If UI changes require backend/program changes outside UI ownership:
  - UI sub-agent must report required backend change points to the main agent.
  - Main agent performs backend/program code changes.
- UI sub-agent must report in Korean by default.
- Before executing UI work, always check and follow:
  - `skills/ui-management/SKILL.md`

## Security & Configuration Tips
- Treat `.env` as local-only and never commit secrets.
- Remove or sanitize sensitive account/trade artifacts before sharing (`*.json`, `assets.xlsx`, backups).
- Prefer configurable paths and environment variables over hardcoded machine-specific values.
