# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python-based crypto portfolio/trade analysis workspace.

- Core orchestration: `main.py`
- Wallet/domain models: `CoinWallet.py`, `CoinAsset.py`
- Exchange and wallet adapters: `Binance_Reader.py`, `Bithumb_Reader.py`, `Gateio_Reader.py`, `GateioV2API.py`, `PersonalWallet_Reader.py`, `Reader.py`
- UI/report entry points: `app.py`, `main_simulation.py`
- Utility/history scripts: `HistoryManager.py`, `renamefiles.py`
- Ad-hoc test scripts: `main_test.py`, `main_test_2.py`
- Repository workflow skills: `skills/git-management/SKILL.md`, `skills/ui-management/SKILL.md`
- Data artifacts: `assets.xlsx`, `assets.html`, `simulation_report.html`, `history/`, `autoinvest/`, `history_backup*/`, `*.json`
- Environment templates: `.env.example`; local secrets live in `.env`

Keep exchange-specific logic inside each `*_Reader.py` file; keep cross-exchange aggregation in `main.py` and wallet/model files.
Keep personal wallet JSON loading in `PersonalWallet_Reader.py`. Keep Flask UI changes in `app.py` per the UI agent rule below.

## Build, Test, and Development Commands
Use PowerShell in the repository root for the normal Windows workflow. Bash also works for syntax checks in Linux/Codespaces.

- `python -m venv .venv` then `.venv\Scripts\Activate.ps1`: create and activate local environment
- `pip install -r requirements.txt`: install Python dependencies
- `python main.py`: run the main aggregation/export workflow and export Excel by default
- `python main.py --output-format both`: export both `assets.xlsx` and `assets.html`
- `python app.py`: run the Flask live dashboard at `http://127.0.0.1:5000`
- `python main_simulation.py --btc-price 70000`: generate a BTC price simulation HTML report
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
- For UI/dashboard work, at minimum run `python -m py_compile *.py`; when feasible, also run `python app.py` and verify the dashboard renders.

## Commit & Pull Request Guidelines
Git metadata is available in this directory. Follow `skills/git-management/SKILL.md` for branch, commit, and push policy.

- Commit message format: `type(scope): summary` (example: `fix(reader): handle empty trade history`)
- Keep commits small and single-purpose.
- PRs should include: purpose, changed files, run commands, and sample output/screenshots for report or Excel changes.
- Reference related issue/task IDs when available.
- Do not include unrelated local changes in commits; stage only intended files/hunks.

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
- Use `.env.example` as the public template for required keys.
- Remove or sanitize sensitive account/trade artifacts before sharing (`*.json`, `assets.xlsx`, `assets.html`, `simulation_report.html`, `history/`, `autoinvest/`, backups).
- Prefer configurable paths and environment variables over hardcoded machine-specific values.
- `PERSONAL_WALLET_FILE` controls the local personal wallet JSON path and defaults to `personal_wallet_assets.json`.
