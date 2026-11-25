from html.parser import HTMLParser
from urllib.parse import urlsplit

import pytest


class CSRFTokenParser(HTMLParser):
    token = None

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == "input" and fields.get("name") == "csrf_token":
            self.token = fields.get("value")


# Public laboratory accounts from the synthetic seed.
ACCOUNTS = {
    "jdoe": ("password1", "Jane Doe"),
    "rsmith": ("letmein", "Rob Smith"),
    "achen": ("Summer2026", "Ada Chen"),
    "admin": ("admin", "System Admin"),
}


def sign_in(client, username):
    password, display_name = ACCOUNTS[username]
    login_page = client.get("/login")
    assert login_page.status_code == 200
    parser = CSRFTokenParser()
    parser.feed(login_page.get_data(as_text=True))
    assert parser.token, "Login form did not supply a CSRF token"
    response = client.post("/login", data={
        "username": username, "password": password, "csrf_token": parser.token,
    })
    assert response.status_code == 302
    assert urlsplit(response.headers["Location"]).path == "/"
    homepage = client.get("/")
    assert homepage.status_code == 200
    assert f"Signed in as {display_name}." in homepage.get_data(as_text=True)


@pytest.mark.parametrize(("path", "protected_content"), [
    ("/claim/3", "Tesco"),
    ("/receipt?f=claim-3.txt", "Meridian Expenses - receipt for claim 3"),
])
@pytest.mark.parametrize(("username", "expected_status"), [
    (None, 302), ("jdoe", 404), ("rsmith", 200), ("achen", 200), ("admin", 200),
])
def test_claim_and_receipt_follow_ownership_policy(
    client, path, protected_content, username, expected_status,
):
    if username is not None:
        sign_in(client, username)
    response = client.get(path)
    assert response.status_code == expected_status
    assert (protected_content in response.get_data(as_text=True)) == (expected_status == 200)
    if expected_status == 302:
        assert urlsplit(response.headers["Location"]).path == "/login"


@pytest.mark.parametrize(("path", "protected_content", "username", "expected_status"), [
    ("/admin/users", "Jane Doe", None, 302),
    ("/admin/users", "Jane Doe", "jdoe", 403),
    ("/admin/users", "Jane Doe", "achen", 403),
    ("/admin/users", "Jane Doe", "admin", 200),
    ("/export?month=2026-09", "Tesco", None, 302),
    ("/export?month=2026-09", "Tesco", "jdoe", 403),
    ("/export?month=2026-09", "Tesco", "achen", 200),
    ("/export?month=2026-09", "Tesco", "admin", 200),
])
def test_privileged_routes_follow_role_policy(
    client, path, protected_content, username, expected_status,
):
    if username is not None:
        sign_in(client, username)
    response = client.get(path)
    assert response.status_code == expected_status
    assert (protected_content in response.get_data(as_text=True)) == (expected_status == 200)
    if expected_status == 302:
        assert urlsplit(response.headers["Location"]).path == "/login"
    if path.startswith("/export") and expected_status == 200:
        assert response.mimetype == "text/csv"
