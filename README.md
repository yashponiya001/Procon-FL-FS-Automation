# QA Automation Framework

CSV-driven Selenium automation for FleetLocate / ForceFieldShare web applications,
plus a small Playwright + pytest framework.

## Folder layout

| Path | What it is |
|---|---|
| `Improved_Selenium_Smart.py` | Main runner. Reads `ExecutionSequence.csv` and runs each module marked `RUN=YES`. |
| `ExecutionSequence.csv` | List of modules (one per locator CSV), test URL, and `RUN` flag. Results are written back here. |
| `LocatorsFiles/` | One CSV per module: step description, locator type/value, action, test data. |
| `record_to_csv.py` | Records a browser session with Playwright codegen and converts it to a module CSV. |
| `playwright_framework/` | Separate Playwright/pytest framework (see its own `.env.example`). |
| `Litmus_Web_Automation_Script.py` | Older legacy runner (uses `SanityFilePaths.csv`). |
| `REPORTS/`, `RESULTS/`, `SCREENSHOT/`, `logs/` | Output folders, created empty. |

## Setup

1. Install Python 3.13 and Google Chrome.
2. Clone the repo and install dependencies:
   ```
   git clone <repo-url>
   cd QA-Automation
   pip install -r requirements.txt
   playwright install chromium
   ```
3. **Passwords:** login passwords were removed before upload. In each file under
   `LocatorsFiles/`, the login row's test data is `<PASSWORD>`. Replace it with the
   real password locally (ask the team lead), and **do not commit** that change.
4. Optional: set `ANTHROPIC_API_KEY` to enable the AI vision fallback for locators.
5. Legacy Litmus script only: edit the paths in `SanityFilePaths.csv` and the
   hard-coded path near line 1145 of `Litmus_Web_Automation_Script.py`.

## Running

1. In `ExecutionSequence.csv`, set `RUN` to `YES` for **one** module and `NO` for the rest.
2. Run:
   ```
   python Improved_Selenium_Smart.py
   ```
3. Check results in `ExecutionSequence.csv`, `REPORTS/` and `logs/`.

Run modules one at a time: finish one, then switch `RUN=YES` to the next.

## Notes

- `SELECT_OPTION` does not work on react-select dropdowns. Use `ENTER_TEXT_ENTER` on
  the dropdown's input instead.
- `PAUSE` steps need a visible console window.
