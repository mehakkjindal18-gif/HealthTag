"""Mobile-number login for HealthTag owners. Plugs into app.py without editing it."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3

from flask import (Blueprint, abort, flash, redirect, render_template_string,
                   request, session, url_for)

from app import (app, db, DB_PATH, sha256_hex, hits, record_hit, clear_hits,
                 client_ip, grant_owner, owner_ok, load_profile, log_event, iso)

bp = Blueprint("owner_auth", __name__)
BOOT_ID = secrets.token_hex(8)

# --- own table, created if missing (the profiles table is untouched) ---
_conn = sqlite3.connect(DB_PATH)
_conn.execute("""CREATE TABLE IF NOT EXISTS owner_logins (
    pid TEXT PRIMARY KEY, phone_hash TEXT NOT NULL, created_at TEXT)""")
_conn.execute("CREATE INDEX IF NOT EXISTS owner_logins_phone ON owner_logins (phone_hash)")
_conn.commit()
_conn.close()


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) >= 10 else ""


def phone_hash(phone):
    # Keyed hash: the number itself is never stored. Needs a stable HEALTHTAG_SECRET_KEY.
    return hmac.new(app.secret_key.encode(), f"phone:{phone}".encode(), hashlib.sha256).hexdigest()


LOGIN_PAGE = """{% extends "base.html" %}
{% block title %}Owner login{% endblock %}
{% block content %}
<h1>Owner login</h1>
<p class="muted">Sign in with your mobile number and the private code shown when you created your HealthTag.</p>
<form method="post" class="panel">
  <div class="row"><label for="phone">Your mobile number</label>
    <input id="phone" name="phone" type="tel" inputmode="numeric" autocomplete="tel" required></div>
  <div class="row"><label for="code">Private code</label>
    <input id="code" name="code" type="password" autocomplete="current-password" required>
    <p class="help">You can also paste your whole private link here.</p></div>
  <button class="btn block" type="submit">Log in</button>
</form>
<p class="fine">New here? <a href="{{ url_for('register') }}">Create a HealthTag</a></p>
{% endblock %}"""

LINK_PAGE = """{% extends "base.html" %}
{% block title %}Set up your login{% endblock %}
{% block content %}
<h1>Set up your login</h1>
{% if code %}
<div class="panel locked">
  <h3>Your private code. Save it now.</h3>
  <p class="fine">It is shown only once. It is your password.</p>
  <code style="word-break:break-all;font-size:1rem;display:block;padding:.5rem;background:rgba(0,0,0,.04);border-radius:4px">{{ code }}</code>
</div>
{% endif %}
<form method="post" class="panel">
  <div class="row"><label for="phone">Your own mobile number</label>
    <input id="phone" name="phone" type="tel" inputmode="numeric" autocomplete="tel" placeholder="98XXXXXXXX" required>
    <p class="help">You will log in with this number and your private code. This is not your emergency contact's number.</p></div>
  <button class="btn coral block" type="submit">Save and continue</button>
</form>
{% endblock %}"""

PROFILES_PAGE = """{% extends "base.html" %}
{% block title %}My profiles{% endblock %}
{% block content %}
<h1>My profiles</h1>
{% for p in profiles %}
<section class="panel">
  <h2 style="margin:0">{{ p.name }}</h2>
  <p class="fine">Code: {{ p.id }}</p>
  <div class="actions">
    <a class="btn" href="{{ url_for('card', pid=p.id) }}">Open card</a>
    <a class="btn ghost" href="{{ url_for('owner', pid=p.id) }}">Dashboard</a>
  </div>
</section>
{% else %}
<p class="muted">No profiles signed in on this browser.</p>
{% endfor %}
<div class="actions">
  <a class="btn ghost" href="{{ url_for('owner_auth.owner_login') }}">Log in to another profile</a>
  <a class="btn coral" href="{{ url_for('register') }}">Create another HealthTag</a>
</div>
{% endblock %}"""


@bp.route("/owner/login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        phone = normalize_phone(request.form.get("phone", ""))
        code = request.form.get("code", "").strip()
        if "k=" in code:                      # allow pasting the full private link
            code = code.split("k=")[-1].strip()
        ip = client_ip()
        if hits("olog_ip", ip, 15) >= 30 or hits("olog_phone", phone or "none", 15) >= 10:
            abort(429)
        rows = []
        if phone:
            rows = db().execute(
                "SELECT p.id, p.owner_key FROM owner_logins l JOIN profiles p ON p.id = l.pid "
                "WHERE l.phone_hash=?", (phone_hash(phone),)).fetchall()
        code_hash = sha256_hex(code).encode()
        for row in rows:
            if secrets.compare_digest(code_hash, row["owner_key"].encode()):
                clear_hits("olog_phone", phone)
                grant_owner(row["id"], row["owner_key"])
                log_event(row["id"], 0, "Owner", "signed in with mobile number and code")
                return redirect(url_for("card", pid=row["id"]))
        record_hit("olog_ip", ip)
        record_hit("olog_phone", phone or "none")
        flash("That mobile number and code don't match.")
    return render_template_string(LOGIN_PAGE)


@bp.route("/owner/logout")
def owner_logout():
    session.pop("owner", None)
    return redirect(url_for("home"))


@bp.route("/owner/profiles")
def my_profiles():
    profiles = []
    for pid in list(session.get("owner", {}).keys()):
        p = load_profile(pid)
        if p and owner_ok(pid, p["owner_key"]):
            profiles.append(p)
    return render_template_string(PROFILES_PAGE, profiles=profiles)


@bp.route("/owner/<pid>/phone", methods=["GET", "POST"])
def link_phone(pid):
    p = load_profile(pid)
    if p is None:
        abort(404)
    if not owner_ok(pid, p["owner_key"]):
        abort(403)                            # only a signed-in owner can set the number
    if request.method == "POST":
        phone = normalize_phone(request.form.get("phone", ""))
        if not phone:
            flash("Enter a valid 10-digit mobile number.")
        else:
            db().execute("INSERT OR REPLACE INTO owner_logins (pid, phone_hash, created_at) VALUES (?,?,?)",
                         (pid, phone_hash(phone), iso()))
            db().commit()
            log_event(pid, 0, "Owner", "linked a mobile number for login")
            return redirect(url_for("card", pid=pid))
    reveal = session.get("reveal")
    code = reveal["k"] if reveal and reveal.get("pid") == pid else None
    return render_template_string(LINK_PAGE, code=code)


def init():
    """Register the pages and send new registrations to the phone-setup step."""
    app.register_blueprint(bp)

    original = app.view_functions["register"]

    def register_then_link_phone():
        resp = original()
        loc = getattr(resp, "location", None)
        if request.method == "POST" and loc and "/card/" in loc:
            return redirect(url_for("owner_auth.link_phone", pid=loc.rstrip("/").split("/")[-1]))
        return resp

    app.view_functions["register"] = register_then_link_phone

    # Optional: sign everyone out whenever the local server restarts
    if os.environ.get("HEALTHTAG_LOGOUT_ON_RESTART") == "1":
        def _fresh_start():
            if session.get("boot") != BOOT_ID:
                session.clear()
                session["boot"] = BOOT_ID
        app.before_request_funcs.setdefault(None, []).insert(0, _fresh_start)
