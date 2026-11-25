# Meridian Expenses - CA1 Remediation Example

This is a **modified assessment copy**, not the original professor-issued application. It is **not independently audited** and must remain on `127.0.0.1` only. Never use these sample accounts or synthetic data in real work.

## Run (Python 3.10+)

Keep the original in a separate directory, then run from this directory:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -c "import secrets; print(secrets.token_hex(32))"
# Set MERIDIAN_SECRET_KEY to the value generated above:
# Windows PowerShell: $env:MERIDIAN_SECRET_KEY="the-generated-64-character-string"
# macOS/Linux: export MERIDIAN_SECRET_KEY="the-generated-64-character-string"
python seed.py
python app.py
```

Then browse to `http://127.0.0.1:5000`. The same four synthetic usernames/passwords from the professor's original README are available; they must **never** be used outside this isolated demonstration. If the original app is still running on port 5000, stop it before starting this copy.

## Security-related changes

- Login uses parameterized SQLite statements and Werkzeug's salted `scrypt` password storage. The seed script rebuilds the database: do **not** run it over an original database you want to preserve.
- Session signing key is provided through an environment variable (not stored in source). Debug mode and the `/debug/config` route are disabled/removed.
- Ownership checks apply to individual claims and corresponding receipts; finance and admin may view all claims. Staff may view their own claims only.
- Administrative user listing is admin-only; CSV exports are finance/admin-only.
- Receipt filenames must match `claim-N.txt`, and `send_from_directory` constrains file serving to the receipts directory.
- Exports use Python's `csv` module, with **no shell**, and actual month filtering through a newly introduced `created_at` column. CSV cells that could be interpreted as spreadsheet formulae receive a protective leading apostrophe.
- Preferences use validated JSON rather than Python pickle. The supported structure is `{ "theme": "light"|"dark", "page_size": integer 5..100 }`.
- Jinja's normal HTML autoescaping is restored for claim notes.
- Added CSRF tokens for form POSTs, a generic login error message, and server-side amount/length checks as additional protections.
- `MERIDIAN_HTTPS=1` enables HTTPS-only session cookies for deployment behind correctly configured TLS; leave it unset for localhost HTTP tests.

## Deliberate limitations

This is an **assessment remediation demonstration**, not a production release. Additional protections would be required for deployment: production WSGI, TLS, logging, monitoring, rate limiting, dependency management, migrations, password policy, a proper testing suite and an independent security review. Four weak demonstration passwords remain unchanged *as account passwords* for the exercise, though their storage is stronger. Some seeded receipts will not correspond to claims created later without a receipt-upload workflow.
