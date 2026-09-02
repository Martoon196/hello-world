#!/usr/bin/env bash
# TASK 2 (server side) — Create the "The Paddock" list and a double-opt-in
# confirmation template in Brevo. Prints the two IDs for apex-config.php.
# Usage: BREVO_KEY=xkeysib-... bash apex/provision_brevo.sh
set -euo pipefail
: "${BREVO_KEY:?set BREVO_KEY=xkeysib-...}"

API="https://api.brevo.com/v3"
req() { curl -fsS -H "api-key: $BREVO_KEY" -H "accept: application/json" \
        -H "content-type: application/json" "$@"; }
jqget() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d$1)"; }

echo "== Folder =="
FOLDER_ID=$(req "$API/contacts/folders?limit=50" \
  | python3 -c "import sys,json;print(next((f['id'] for f in json.load(sys.stdin).get('folders') or [] if f['name']=='Apex Code'),''))")
if [ -z "$FOLDER_ID" ]; then
  FOLDER_ID=$(req -X POST "$API/contacts/folders" -d '{"name":"Apex Code"}' | jqget "['id']")
fi
echo "folder=$FOLDER_ID"

echo "== List: The Paddock =="
LIST_ID=$(req "$API/contacts/lists?limit=50" \
  | python3 -c "import sys,json;print(next((l['id'] for l in json.load(sys.stdin).get('lists') or [] if l['name']=='The Paddock'),''))")
if [ -z "$LIST_ID" ]; then
  LIST_ID=$(req -X POST "$API/contacts/lists" \
    -d "{\"name\":\"The Paddock\",\"folderId\":$FOLDER_ID}" | jqget "['id']")
fi
echo "BREVO_LIST_ID=$LIST_ID"

echo "== Double opt-in template =="
TEMPLATE_ID=$(req "$API/smtp/templates?limit=50" \
  | python3 -c "import sys,json;print(next((t['id'] for t in json.load(sys.stdin).get('templates') or [] if t['name']=='Apex Paddock DOI'),''))")
if [ -z "$TEMPLATE_ID" ]; then
  TEMPLATE_ID=$(python3 - "$API" <<'PY'
import json, os, subprocess, sys
html = """<!doctype html><html><body style="background:#0A0A0A;color:#F2EDE3;font-family:Arial,sans-serif;padding:32px;text-align:center">
<h1 style="color:#F2EDE3;letter-spacing:2px">THE <span style="color:#ECB02B">APEX</span> CODE</h1>
<p>One click and you're in The Paddock — the free tier. One tip a week, the full log every Sunday, nothing else.</p>
<p style="margin:28px 0"><a href="{{ doubleoptin }}" style="background:#ECB02B;color:#111;padding:12px 28px;text-decoration:none;font-weight:bold;border-radius:6px">CONFIRM MY SPOT</a></p>
<p style="color:#9A948A;font-size:12px">If you didn't sign up at apexcode.uk, ignore this email.</p>
<p style="color:#9A948A;font-size:12px">18+ · BeGambleAware.org</p>
</body></html>"""
body = {
    "templateName": "Apex Paddock DOI",
    "subject": "Confirm your spot in The Paddock",
    "sender": {"name": "The Apex Code", "email": "no-reply@apexcode.uk"},
    "htmlContent": html,
    "isActive": True,
    "tag": "optin",
}
out = subprocess.run(
    ["curl", "-fsS", "-X", "POST", sys.argv[1] + "/smtp/templates",
     "-H", "api-key: " + os.environ["BREVO_KEY"],
     "-H", "content-type: application/json", "-d", json.dumps(body)],
    capture_output=True, text=True, check=True)
print(json.loads(out.stdout)["id"])
PY
)
fi
echo "BREVO_DOI_TEMPLATE_ID=$TEMPLATE_ID"

echo
echo "NOTE: Brevo requires DOI templates to carry the {{ doubleoptin }} link and be"
echo "flagged for opt-in use. If the API send later returns a template error, open"
echo "Brevo -> Templates -> 'Apex Paddock DOI' and save it once under"
echo "Forms/Double opt-in as the confirmation template, keeping the same ID."
