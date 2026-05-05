# UI Management Skill

## Purpose
This skill defines UI-related responsibilities in `cryptonote_renewal`.
UI includes both:
- Excel output structure
- HTML output structure

Use this skill whenever a request changes report layout, columns, ordering, style, labels, or presentation rules.

## Scope Ownership
- Excel UI owner file:
  - `CoinWallet.py`
  - Primary method: `export_assets_to_excel(...)`
- HTML UI owner file:
  - `app.py` (Flask web UI)
  - `main.py` static HTML method: `export_assets_to_html(...)`

## Core Rules
1. Keep data-calculation logic and UI-rendering logic separated.
- Calculation updates should stay in calculation functions.
- Layout/format updates should stay in export/render functions.

2. Excel UI changes must be explicit.
- Define/modify column names, order, rounding, and summary rows in one place (`export_assets_to_excel`).
- If metric labels change in Excel, apply consistent naming across all summary rows.

3. HTML UI changes must be explicit.
- Update table headers and row cell order together.
- Keep summary cards and table metrics consistent with wallet fields.
- Preserve UTF-8 output and valid HTML structure.

4. Backward safety.
- Do not remove existing key fields unless requested.
- Prefer additive UI changes (new columns/sections) over breaking removals.

5. UI/Backend split rule.
- UI sub-agent owns UI-layer code changes, including `app.py`.
- If a UI request requires backend/program behavior changes outside UI ownership
  (for example, reader orchestration, domain computation, API integration, data model changes):
  - UI sub-agent must first report required backend change points to the main agent.
  - Main agent applies backend changes.
- UI sub-agent should not directly change non-UI backend logic unless explicitly delegated by the main agent.

## Change Playbook
When handling UI requests:
1. Classify request:
- Excel-only
- HTML-only
- Both
2. Edit only responsible files/methods first.
2.1 If backend change is needed, stop and report:
- exact file/function to change
- why UI cannot be completed without it
- expected input/output after backend change
3. Verify run path:
- `python main.py --output-format excel`
- `python main.py --output-format html`
- `python main.py --output-format both`
4. Report exactly what changed:
- file
- section/method
- user-visible effect

## Common Task Mapping
- Change Excel column order/labels:
  - edit `CoinWallet.py::export_assets_to_excel`
- Change HTML table columns/styles/cards:
  - edit `app.py` (Flask UI) or `main.py::export_assets_to_html` (static export)
- Add new displayed metric in both reports:
  - compute value in wallet/main logic
  - wire to both export methods

## Reporting Language
- UI sub-agent reports to the user in Korean by default.

## Extensibility
- This skill is extendable.
- Add new sections for charting, theming, localization, or frontend split as needed.
