#!/usr/bin/env python3
"""
renewal_to_contacts.py
----------------------
Imports a renewal table copied from Apple Mail into Apple Contacts.

Workflow:
    1. Select and copy the renewal table in Apple Mail (Cmd+C)
    2. python3 renewal_to_contacts.py
    3. Review the preview, confirm with Y / Enter

What gets stored per contact:
    - Last Name   ← Client Name column
    - Email       ← Client Email column
    - Phone       ← Client Phone column
    - Note        ← Columns 1–4 (Activation date, Expiry date, Quantity, Product)

Match logic:
    - Existing contact found by email  → note is overwritten; phone added if none exists
    - No match                         → new contact created

Requirements: Python 3 and osascript — both built into macOS. No packages needed.
"""

import csv
import io
import subprocess
import sys
from datetime import date


# ── Column name aliases — Dutch and English variants ─────────────────────────
ALIASES: dict[str, list[str]] = {
    "activation":  ["activation date", "activation", "activatiedatum"],
    "expiry":      ["expiry date", "expiry", "vervaldatum", "verloopt"],
    "quantity":    ["quantity", "aantal", "qty"],
    "product":     ["product"],
    "client_name": ["client name", "clientnaam", "naam", "name", "client"],
    "email":       ["client email", "email", "e-mail", "emailadres"],
    "phone":       ["client phone", "telefoon", "phone", "tel", "mobiel", "mobile"],
}

REQUIRED_FIELDS = ("client_name", "email", "phone")


# ── Clipboard ─────────────────────────────────────────────────────────────────

def read_clipboard() -> str:
    """Return plain-text clipboard contents using macOS pbpaste."""
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


# ── Table parser ──────────────────────────────────────────────────────────────

def _find_col(headers: list[str], aliases: list[str]) -> int | None:
    for alias in aliases:
        if alias in headers:
            return headers.index(alias)
    return None


def parse_table(text: str) -> list[dict]:
    """
    Parse tab-separated text (as copied from Apple Mail) into a list of records.
    Detects the header row automatically and maps columns by name.
    """
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))

    # ── Find header row ───────────────────────────────────────────────────────
    header_idx: int | None = None
    for i, row in enumerate(rows):
        normalised = [c.strip().lower() for c in row]
        for field_aliases in ALIASES.values():
            if any(alias in normalised for alias in field_aliases):
                header_idx = i
                break
        if header_idx is not None:
            break

    if header_idx is None:
        sys.exit(
            "ERROR: No recognisable header row found.\n"
            "Make sure you copied the full table including the header row."
        )

    headers = [c.strip().lower() for c in rows[header_idx]]

    # ── Map logical fields → column indices ───────────────────────────────────
    col: dict[str, int | None] = {
        field: _find_col(headers, aliases)
        for field, aliases in ALIASES.items()
    }

    for required in REQUIRED_FIELDS:
        if col[required] is None:
            sys.exit(
                f"ERROR: Could not locate the '{required}' column.\n"
                f"Headers detected: {headers}"
            )

    def cell(row: list[str], key: str) -> str:
        idx = col.get(key)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    today_str = date.today().strftime("%B %d %Y")

    records: list[dict] = []
    for row in rows[header_idx + 1 :]:
        if not any(c.strip() for c in row):
            continue  # skip blank rows

        name  = cell(row, "client_name")
        email = cell(row, "email")

        if not name and not email:
            continue

        if not email:
            print(f"  [SKIP] '{name}' has no email address — skipping (cannot deduplicate).")
            continue

        note = (
            f"Renewal info (imported {today_str}):\n"
            f"  Activation : {cell(row, 'activation')}\n"
            f"  Expiry     : {cell(row, 'expiry')}\n"
            f"  Quantity   : {cell(row, 'quantity')}\n"
            f"  Product    : {cell(row, 'product')}"
        )

        records.append(
            {
                "name":  name,
                "email": email,
                "phone": cell(row, "phone"),
                "note":  note,
            }
        )

    return records


# ── AppleScript helpers ───────────────────────────────────────────────────────

def _as_str(text: str) -> str:
    """Return an AppleScript quoted-string literal for the given Python string."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _as_note_expr(r: dict) -> str:
    """
    Convert the note string to an AppleScript expression using & linefeed &
    concatenation, avoiding literal newlines inside AppleScript string literals.
    """
    return " & linefeed & ".join(_as_str(line) for line in r["note"].splitlines())


def _run_applescript(script: str) -> str:
    """Execute an AppleScript via stdin and return stdout, raising on failure."""
    result = subprocess.run(
        ["osascript"],
        input=script,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def upsert_contact(r: dict) -> str:
    """
    Create a new contact or update an existing one matched by email.
    Returns 'created' or 'updated'.
    """
    email_as  = _as_str(r["email"])
    phone_as  = _as_str(r["phone"])
    name_as   = _as_str(r["name"])
    note_expr = _as_note_expr(r)

    script = f"""\
tell application "Contacts"
    set noteText to {note_expr}
    set matched to (every person whose value of emails contains {email_as})

    if (count of matched) > 0 then
        -- ── UPDATE existing contact ─────────────────────────────────────────
        set thePerson to item 1 of matched
        set note of thePerson to noteText
        if (count of phones of thePerson) = 0 and {phone_as} is not "" then
            make new phone at end of phones of thePerson ¬
                with properties {{label:"work", value:{phone_as}}}
        end if
        save
        return "updated"

    else
        -- ── CREATE new contact ──────────────────────────────────────────────
        set newPerson to make new person with properties {{last name:{name_as}}}
        set note of newPerson to noteText
        if {email_as} is not "" then
            make new email at end of emails of newPerson ¬
                with properties {{label:"work", value:{email_as}}}
        end if
        if {phone_as} is not "" then
            make new phone at end of phones of newPerson ¬
                with properties {{label:"work", value:{phone_as}}}
        end if
        save
        return "created"
    end if
end tell
"""
    return _run_applescript(script)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _load_records() -> list[dict]:
    """Read clipboard and parse table, exiting with a message on failure."""
    text = read_clipboard()
    if not text.strip():
        sys.exit(
            "Clipboard is empty.\n"
            "Select and copy the renewal table in Apple Mail (Cmd+C) first."
        )
    records = parse_table(text)
    if not records:
        sys.exit("No valid data rows found in the clipboard.")
    return records


def _run_import(records: list[dict]) -> str:
    """Import records into Contacts and return a summary string."""
    created = updated = errors = 0
    lines: list[str] = []
    for r in records:
        try:
            action = upsert_contact(r)
            tag = "[NEW]    " if action == "created" else "[UPDATED]"
            lines.append(f"  {tag} {r['name']} <{r['email']}>")
            if action == "created":
                created += 1
            else:
                updated += 1
        except Exception as exc:
            lines.append(f"  [ERROR]  {r['name']} — {exc}")
            errors += 1
    lines.append(f"\nDone — {created} created, {updated} updated, {errors} errors.")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--interactive"

    records = _load_records()

    name_w  = max(max(len(r["name"])  for r in records), 4)
    email_w = max(max(len(r["email"]) for r in records), 5)

    if mode == "--list":
        # Machine-readable preview for the .app dialog
        lines = [f"Found {len(records)} client(s) to import:\n"]
        for r in records:
            lines.append(f"  {r['name']:<{name_w}}  {r['email']:<{email_w}}  {r['phone']}")
        print("\n".join(lines))

    elif mode == "--import":
        # Silent import — output goes to the .app result dialog
        print(_run_import(records))

    else:
        # ── Interactive Terminal mode ─────────────────────────────────────────
        print(f"  {'Name':<{name_w}}  {'Email':<{email_w}}  Phone")
        print(f"  {'─'*name_w}  {'─'*email_w}  {'─'*15}")
        for r in records:
            print(f"  {r['name']:<{name_w}}  {r['email']:<{email_w}}  {r['phone']}")
        print(f"\n  {len(records)} record(s) ready to import.")

        answer = input("\nImport into Apple Contacts? [Y/n] ").strip().lower()
        if answer not in ("", "y", "yes"):
            print("Aborted — no changes made.")
            sys.exit(0)

        print()
        print(_run_import(records))


if __name__ == "__main__":
    main()
