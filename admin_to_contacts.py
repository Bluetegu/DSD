#!/usr/bin/env python3
"""
admin_to_contacts.py
--------------------
Imports an administration table copied from a browser or app into Apple Contacts.

Workflow:
    1. Select and copy the admin table (Cmd+C)
    2. python3 admin_to_contacts.py
    3. Review the preview, confirm with Y / Enter

What gets stored per contact:
    - First Name / Last Name  ← Contact person (split on first space)
    - Organisation            ← Company name  (skipped when N/A)
    - Email                   ← Email column
    - Address                 ← Address + Postal code/City (skipped when N/A)
    - Note                    ← Import date, company and address summary

Match logic:
    - Existing contact found by email  → org/note updated; address added if none exists
    - No match                         → new contact created

Requirements: Python 3 and osascript — both built into macOS. No packages needed.
"""

import csv
import io
import subprocess
import sys
from datetime import datetime


# ── Column name aliases (Dutch / English) ─────────────────────────────────────
ALIASES: dict[str, list[str]] = {
    "company": ["company name", "company", "bedrijf", "bedrijfsnaam",
                "organisation", "organization"],
    "person":  ["contact person", "contact", "person", "naam",
                "contactpersoon", "name"],
    "address": ["address", "adres", "straat", "street"],
    "postal":  ["postal code/city", "postal code/city", "postcode/stad",
                "postcode", "city", "stad"],
    "email":   ["email", "e-mail", "emailadres"],
}

REQUIRED_FIELDS = ("person", "email")

# Values treated as "no data"
NA_VALUES = {"n/a", "n.a.", "-", "", "nvt", "n.v.t."}


# ── Clipboard ─────────────────────────────────────────────────────────────────

def read_clipboard() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


# ── Parsing helpers ───────────────────────────────────────────────────────────

def normalise(value: str) -> str:
    """Return empty string for N/A variants, otherwise the stripped value."""
    return "" if value.strip().lower() in NA_VALUES else value.strip()


def split_name(full: str) -> tuple[str, str]:
    """
    Split a full name into (first, last).
    'Elon Cosla'          → ('Elon', 'Cosla')
    'Wytske van Kerckhoff'→ ('Wytske', 'van Kerckhoff')
    'H. Kloppenborg'      → ('H.', 'Kloppenborg')
    Single word           → ('', word)
    """
    parts = full.strip().split(" ", 1)
    if len(parts) == 1:
        return ("", parts[0])
    return (parts[0], parts[1])


def split_postal_city(value: str) -> tuple[str, str]:
    """
    Parse '3572PN / Utrecht' → ('3572PN', 'Utrecht').
    Returns ('', '') for N/A or unrecognised format.
    """
    if not value or value.strip().lower() in NA_VALUES:
        return ("", "")
    if " / " in value:
        postal, city = value.split(" / ", 1)
        return (postal.strip(), city.strip())
    return ("", value.strip())


# ── Table parser ──────────────────────────────────────────────────────────────

def _find_col(headers: list[str], aliases: list[str]) -> int | None:
    for alias in aliases:
        if alias in headers:
            return headers.index(alias)
    return None


def parse_table(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    today_str = datetime.now().strftime("%B %d %Y, %H:%M")

    # ── Find header row ───────────────────────────────────────────────────────
    header_idx: int | None = None
    for i, row in enumerate(rows):
        norm = [c.strip().lower() for c in row]
        for field_aliases in ALIASES.values():
            if any(a in norm for a in field_aliases):
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
    col: dict[str, int | None] = {
        field: _find_col(headers, aliases)
        for field, aliases in ALIASES.items()
    }

    for req in REQUIRED_FIELDS:
        if col[req] is None:
            sys.exit(
                f"ERROR: Could not find the '{req}' column.\n"
                f"Headers detected: {headers}"
            )

    def cell(row: list[str], key: str) -> str:
        idx = col.get(key)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    records: list[dict] = []
    for row in rows[header_idx + 1:]:
        if not any(c.strip() for c in row):
            continue

        person = cell(row, "person")
        email  = normalise(cell(row, "email"))

        if not person and not email:
            continue
        if not email:
            print(f"  [SKIP] '{person}' has no email — skipping (cannot deduplicate).")
            continue

        company        = normalise(cell(row, "company"))
        address        = normalise(cell(row, "address"))
        postal, city   = split_postal_city(cell(row, "postal"))
        first, last    = split_name(person)

        note_lines = [f"Admin import ({today_str}):"]
        if company:
            note_lines.append(f"  Company : {company}")
        if address:
            note_lines.append(f"  Address : {address}")
        if postal or city:
            note_lines.append(f"  Postal  : {postal}   City : {city}")

        records.append({
            "first":   first,
            "last":    last,
            "email":   email,
            "company": company,
            "address": address,
            "postal":  postal,
            "city":    city,
            "note":    "\n".join(note_lines),
        })

    return records


# ── AppleScript helpers ───────────────────────────────────────────────────────

def _as_str(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _as_note_expr(note: str) -> str:
    return " & linefeed & ".join(_as_str(line) for line in note.splitlines())


def _run_applescript(script: str) -> str:
    result = subprocess.run(["osascript"], input=script, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _build_batch_script(records: list[dict]) -> str:
    """
    Generate a single AppleScript that processes every record inside one
    'tell application Contacts' block with one save at the end.
    This avoids repeated Apple Event round-trips that cause timeout errors.

    Each record emits one output line:
        created|Full Name|email
        updated|Full Name|email
        error|Full Name|email|message
    """
    parts: list[str] = [
        'tell application "Contacts"',
        '    set output to ""',
        '',
    ]

    for r in records:
        email_as   = _as_str(r["email"])
        first_as   = _as_str(r["first"])
        last_as    = _as_str(r["last"])
        note_expr  = _as_note_expr(r["note"])
        name_as    = _as_str(f"{r['first']} {r['last']}".strip())
        has_addr   = bool(r["address"] or r["postal"] or r["city"])
        address_as = _as_str(r["address"])
        postal_as  = _as_str(r["postal"])
        city_as    = _as_str(r["city"])

        block: list[str] = [
            f'    -- {r["first"]} {r["last"]} <{r["email"]}>',
            f'    try',
            f'        set noteText to {note_expr}',
            f'        set matched to (every person whose value of emails contains {email_as})',
            f'        if (count of matched) > 0 then',
            f'            -- UPDATE existing contact',
            f'            set thePerson to item 1 of matched',
            f'            set note of thePerson to noteText',
        ]

        if r["company"]:
            block.append(f'            set organization of thePerson to {_as_str(r["company"])}')

        if has_addr:
            block += [
                f'            if (count of addresses of thePerson) > 0 then',
                f'                set street of item 1 of addresses of thePerson to {address_as}',
                f'                set zip of item 1 of addresses of thePerson to {postal_as}',
                f'                set city of item 1 of addresses of thePerson to {city_as}',
                f'            else',
                f'                make new address at end of addresses of thePerson ¬',
                f'                    with properties {{label:"home", street:{address_as}, zip:{postal_as}, city:{city_as}}}',
                f'            end if',
            ]

        block += [
            f'            set output to output & "updated|" & {name_as} & "|" & {email_as} & linefeed',
            f'        else',
            f'            -- CREATE new contact',
            f'            set newPerson to make new person with properties ¬',
            f'                {{first name:{first_as}, last name:{last_as}}}',
        ]

        if r["company"]:
            block.append(f'            set organization of newPerson to {_as_str(r["company"])}')

        block.append(
            f'            make new email at end of emails of newPerson ¬'
            f'\n                with properties {{label:"work", value:{email_as}}}'
        )

        if has_addr:
            block.append(
                f'            make new address at end of addresses of newPerson ¬'
                f'\n                with properties {{label:"home", street:{address_as}, zip:{postal_as}, city:{city_as}}}'
            )

        block += [
            f'            set note of newPerson to noteText',
            f'            set output to output & "created|" & {name_as} & "|" & {email_as} & linefeed',
            f'        end if',
            f'    on error errMsg',
            f'        set output to output & "error|" & {name_as} & "|" & {email_as} & "|" & errMsg & linefeed',
            f'    end try',
            '',
        ]

        parts.extend(block)

    parts += [
        '    save',
        '    return output',
        'end tell',
    ]

    return "\n".join(parts)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _load_records() -> list[dict]:
    text = read_clipboard()
    if not text.strip():
        sys.exit("Clipboard is empty.\nSelect and copy the admin table first (Cmd+C).")
    records = parse_table(text)
    if not records:
        sys.exit("No valid data rows found.")
    return records


def _run_import(records: list[dict]) -> str:
    """Run all upserts in a single AppleScript call and return a summary string."""
    script = _build_batch_script(records)
    raw    = _run_applescript(script)

    created = updated = errors = 0
    lines: list[str] = []

    for line in raw.strip().splitlines():
        parts = line.split("|", 3)
        if not parts:
            continue
        action = parts[0]
        name   = parts[1] if len(parts) > 1 else "?"
        email  = parts[2] if len(parts) > 2 else "?"
        if action == "created":
            lines.append(f"  [NEW]     {name} <{email}>")
            created += 1
        elif action == "updated":
            lines.append(f"  [UPDATED] {name} <{email}>")
            updated += 1
        elif action == "error":
            msg = parts[3] if len(parts) > 3 else ""
            lines.append(f"  [ERROR]   {name} — {msg}")
            errors += 1

    lines.append(f"\nDone — {created} created, {updated} updated, {errors} errors.")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--interactive"

    records = _load_records()

    name_w  = max(max(len(f"{r['first']} {r['last']}") for r in records), 4)
    email_w = max(max(len(r["email"]) for r in records), 5)

    if mode == "--list":
        lines = [f"Found {len(records)} contact(s) to import:\n"]
        for r in records:
            name = f"{r['first']} {r['last']}".strip()
            lines.append(f"  {name:<{name_w}}  {r['email']:<{email_w}}  {r['company']}")
        print("\n".join(lines))

    elif mode == "--import":
        print(_run_import(records))

    else:
        # ── Interactive Terminal mode ─────────────────────────────────────────
        print(f"  {'Name':<{name_w}}  {'Email':<{email_w}}  Company")
        print(f"  {'─'*name_w}  {'─'*email_w}  {'─'*20}")
        for r in records:
            name = f"{r['first']} {r['last']}".strip()
            print(f"  {name:<{name_w}}  {r['email']:<{email_w}}  {r['company']}")
        print(f"\n  {len(records)} record(s) ready to import.")

        answer = input("\nImport into Apple Contacts? [Y/n] ").strip().lower()
        if answer not in ("", "y", "yes"):
            print("Aborted — no changes made.")
            sys.exit(0)

        print()
        print(_run_import(records))


if __name__ == "__main__":
    main()
