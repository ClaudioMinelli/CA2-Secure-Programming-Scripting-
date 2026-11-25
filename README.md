# Meridian Expenses — CA2 security pipeline

Flask and SQLite expense-claims laboratory with synthetic accounts and data. Based on the CA1 remediation copy. Run it on localhost. See [README-CA1.md](README-CA1.md) for the application controls and laboratory limitations.

## Local setup on Windows PowerShell

Open the project folder in VS Code. Run these commands from its root:

```powershell
py -3.12 -m venv .venv
$Python = ".\.venv\Scripts\python.exe"
& $Python -m pip install -r requirements.txt -r requirements-dev.txt
New-Item -ItemType Directory -Force evidence | Out-Null
& $Python -m pytest tests/security -v --junitxml=evidence/access-policy.xml
```

The test fixture generates a session key, seeds a temporary directory, and gives each case a fresh copy of the database. It uses the Flask test client. The server and a project-root database are unnecessary for the checks.

## Access policy

- Staff can access their own claims and receipts. Staff requesting another user's resources receive 404; finance and administrators can access existing claims and receipts.
- Only administrators can list users. Finance and administrators can export claims. Staff are refused both operations.
- Anonymous users are redirected to login. Each authenticated test verifies the login identity before testing the protected route. Tests cover the response body as well as status.

## Local evidence

Run the following from the same PowerShell session:

```powershell
& $Python -m bandit app.py seed.py -f json -o evidence/bandit.json --exit-zero
& $Python scripts/check_bandit.py evidence/bandit.json
py -3.12 -m venv .sca-venv
$RuntimePython = ".\.sca-venv\Scripts\python.exe"
& $RuntimePython -m pip install -r requirements.txt
& $RuntimePython -m pip freeze | Set-Content -Encoding ascii evidence/runtime-resolved.txt
& $Python -m pip_audit -r evidence/runtime-resolved.txt --no-deps --disable-pip -f json -o evidence/pip-audit.json
```

Check each command's exit code and keep the output. If setup fails, resolve it before using the scan results. The frozen list captures the observed runtime dependency tree for each run. The baseline manifest pins only Flask, so transitive installs can change between runs. The audit needs access to an advisory service.

## GitHub Actions

The [Security workflow](.github/workflows/security.yml) runs on pull requests to main, pushes to main, weekly and on manual dispatch. The four jobs upload their reports separately. Require the **Security gate** status check in the ruleset for main and require changes through pull requests. Test evaluator access to the repository and evidence before submission.

The initial policy blocks high-severity, high-confidence Bandit findings, known advisory findings from pip-audit, Gitleaks matches and access-policy failures. Lower-priority Bandit findings are printed as warnings. A failed or skipped security job blocks the aggregate gate. Scanner scope is recorded in each job. Git history coverage extends to refs fetched by the runner. The workflow uses read-only repository permissions and pins reusable actions by full commit SHA.

Keep raw evidence private and review it before including extracts in a report. Record each run's commit, URL, tool versions, findings, triage decisions and timings. Interpret warnings and failures using the report for that run.
