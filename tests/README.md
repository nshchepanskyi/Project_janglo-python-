# GrandStay Selenium UI tests

Python/Django application UI is tested with Selenium WebDriver + pytest; the app itself is not changed to accommodate the test suite. The authoritative case descriptions are extracted in `case_inventory.json` from every sheet of `GRNDST-0003.xlsx` and `GRNDST-0002.xlsx`; automated test names and `case_id` markers retain the original IDs.

## Verified case coverage

| Excel ID and title | Automated coverage | Limits |
|---|---|---|
| `GRNDST-0003` — Authorization with valid credentials | Home → Sign In → email/password → authenticated profile; verifies profile email | Requires the provided existing test account. Login only creates a browser session and does not mutate application data. |
| `GRNDST-0002` — Signing out from the webpage | Logs in with a dedicated account, opens home as required by the Excel precondition, submits Logout, verifies the login and anonymous home pages, then uses browser Back and verifies authenticated controls stay absent | Requires dedicated credentials. Login/logout do not create or change persistent app data. |

Selectors, paths, and copy are verified against Django URL patterns and `hotel/templates/hotel/{base_public,login,register,verify_email}.html`. Django uses PostgreSQL (`DATABASE_URL` on Render; local `DB_*` / `DB_ENGINE` defaults to PostgreSQL). The existing project also contains Django tests and an older `e2e_tests/base.py`; these pytest tests are separately runnable and do not alter Django app architecture. Render's hostname is deliberately not assumed.

## Setup and run

From the repository root:

```powershell
python -m pip install -r tests/requirements.txt
# Start the local Django app in another terminal, with its normal .env/database configured:
python manage.py runserver
# Run tests; server readiness is checked for up to STARTUP_TIMEOUT seconds (default 90):
python -m pytest -c tests/pytest.ini tests/test_cases -v --html=tests/reports/report.html --self-contained-html
# One module:
python -m pytest -c tests/pytest.ini tests/test_cases/test_logout.py -v
```

Configuration via `tests/.env` (git-ignored) or environment (or `--base-url`):

```text
BASE_URL=http://127.0.0.1:8000
BROWSER=chrome                 # chrome or firefox
HEADLESS=false
WAIT_SECONDS=15
STARTUP_TIMEOUT=90
CHROMEDRIVER_PATH=...          # optional; otherwise Selenium Manager
```

`tests/.env` holds local-only test settings and is ignored by Git. Both cases use `TEST_LOGIN_USERNAME` and `TEST_LOGIN_PASSWORD`; the same dedicated account is used for authorization then logout. Use only a test deployment, never production. The login/logout tests do not create or change persistent app data. `.env` secrets are not printed in the report.

HTML report output and failure screenshots are written to `tests/reports/`; screenshots are linked from pytest-html failure details. Assertions include case ID and the actual page/state in their failure messages. `pytest-html` records pass/fail/skip and pytest's failure detail; skipped test output states the unmet precondition.

## Excel source

The inventory preserves IDs, titles, preconditions, descriptions, sheet names, and each numbered step with its action, test data, and expected result. To regenerate it after updating the source workbooks, use `utils.excel_reader.read_workbook()` from the `tests` directory and write the combined results to `case_inventory.json`. Source workbook names: `GRNDST-0003.xlsx`, `GRNDST-0002.xlsx`.
