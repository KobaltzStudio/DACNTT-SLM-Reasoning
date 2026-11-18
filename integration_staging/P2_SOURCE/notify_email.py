#!/usr/bin/env python3
"""
Send a short e-mail (e.g. when run_all.sh ends). Standard library only.

SMTP settings and addresses come from a .env file (default: experiments/week2September/manual/.env), never
from the command line, so they do not end up in logs or shell history. .env is git-ignored; copy
.env.example and fill it in. For Gmail: turn on 2-step verification and create an App Password
(https://myaccount.google.com/apppasswords); the normal account password does not work over SMTP.

  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587                 # 587 = STARTTLS, 465 = SSL
  SMTP_USER=...                 # login, usually the sender address
  SMTP_PASSWORD=...             # app password
  MAIL_FROM=...                 # optional, defaults to SMTP_USER
  MAIL_TO=...                   # one or more addresses, comma-separated

Without any password: ntfy.sh (no account). Set NTFY_TOPIC (a long random name: anyone who knows it can read
the messages) and optionally NTFY_EMAIL; ntfy.sh then pushes to its app / web page and e-mails NTFY_EMAIL.
The message (status + last log lines) passes through ntfy.sh. When NTFY_TOPIC is set the SMTP keys are not
needed.

  NTFY_TOPIC=dacntt-runs-8f3k2q9x7m
  NTFY_EMAIL=you@example.com     # optional
  NTFY_SERVER=https://ntfy.sh    # optional

Usage:
  python scripts/notify_email.py --subject "seed 13 finished" --body "text" [--log runs/main/log_seed13.txt]
  python scripts/notify_email.py --test        # send a test message to check the settings
Exit code 1 when sending fails (the caller decides whether that matters).
"""
import argparse
import os
import smtplib
import socket
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

DEFAULT_ENV = Path(__file__).resolve().parent.parent / ".env"
REQUIRED = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_TO")
NTFY_KEYS = ("NTFY_TOPIC", "NTFY_EMAIL", "NTFY_SERVER")


def read_env(path):
    """KEY=VALUE lines; '#' comments and surrounding quotes allowed. Process environment overrides the file."""
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.split(" #", 1)[0].strip().strip('"').strip("'")
            values[key.strip()] = value
    for key in REQUIRED + ("MAIL_FROM",) + NTFY_KEYS:
        if os.environ.get(key):
            values[key] = os.environ[key]
    if values.get("NTFY_TOPIC"):
        return values
    missing = [k for k in REQUIRED if not values.get(k)]
    if missing:
        raise SystemExit(f"missing in {path}: {', '.join(missing)} (see .env.example)")
    return values


def tail(path, n):
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


def send_ntfy(env, subject, body):
    import urllib.request
    url = f"{env.get('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')}/{env['NTFY_TOPIC']}"
    # HTTP headers must be latin-1: keep the title ASCII, the body (UTF-8) carries the details
    headers = {"Title": subject.encode("ascii", "replace").decode(), "Tags": "computer"}
    if env.get("NTFY_EMAIL"):
        headers["Email"] = env["NTFY_EMAIL"]
    req = urllib.request.Request(url, data=body[-3500:].encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise OSError(f"ntfy answered HTTP {resp.status}")


def send(env, subject, body):
    if env.get("NTFY_TOPIC"):
        send_ntfy(env, subject, body)
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = env.get("MAIL_FROM") or env["SMTP_USER"]
    msg["To"] = env["MAIL_TO"]
    msg.set_content(body)
    port = int(env["SMTP_PORT"])
    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(env["SMTP_HOST"], port, context=context, timeout=30)
    else:
        server = smtplib.SMTP(env["SMTP_HOST"], port, timeout=30)
        server.starttls(context=context)
    with server:
        password = env["SMTP_PASSWORD"]
        if "gmail" in env["SMTP_HOST"]:  # Gmail shows app passwords in groups of four: "abcd efgh ijkl mnop"
            password = password.replace(" ", "")
        server.login(env["SMTP_USER"], password)
        server.send_message(msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject")
    ap.add_argument("--body", default="")
    ap.add_argument("--log", type=Path, help="append the last --log-lines lines of this file")
    ap.add_argument("--log-lines", type=int, default=40)
    ap.add_argument("--env", type=Path, default=DEFAULT_ENV)
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    env = read_env(args.env)
    host = socket.gethostname()
    subject = args.subject or "[DACNTT] test message"
    body = args.body or ("Test message from notify_email.py: the SMTP settings work." if args.test else "")
    if args.log and args.log.exists():
        body += f"\n\n--- last {args.log_lines} lines of {args.log} ---\n{tail(args.log, args.log_lines)}"
    body += f"\n\nhost: {host}"
    try:
        send(env, subject, body)
    except (OSError, smtplib.SMTPException) as e:
        print(f"[notify_email] sending failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"[notify_email] sent: {subject}")


if __name__ == "__main__":
    main()
