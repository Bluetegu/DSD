# RenewalToContacts

Imports software renewal clients from Apple Mail into Apple Contacts.

When a renewal email arrives, it contains a table listing clients whose licences are expiring. This tool reads that table and creates or updates each client as a contact in Apple Contacts, storing the renewal details (activation date, expiry date, quantity and product) in the contact's Note field.

---

## How it works

| Contact field | Source column                                   |
| ------------- | ----------------------------------------------- |
| Last Name     | Client name                                     |
| Email         | Client email                                    |
| Phone         | Client phone                                    |
| Note          | Activation date, Expiry date, Quantity, Product |

**Matching logic**
- If a contact with the same email already exists → the Note is updated and a phone number is added if none is present.
- If no match is found → a new contact is created.

---

## Usage (App — no technical knowledge required)

1. Open the renewal email in **Apple Mail**.
2. Select the entire table and copy it — **Cmd+C**.
3. Double-click **`RenewalToContacts.app`**.
4. A dialog shows the list of clients found. Review it.
5. Click **Import** to write them to Apple Contacts.
6. A confirmation dialog reports how many were created and updated.

> **First launch only:** macOS may show an "unidentified developer" warning.  
> Right-click the app → **Open** → **Open**. After that, double-click works normally.

---

## Usage (Terminal — advanced)

```bash
# 1. Copy the table in Apple Mail (Cmd+C)
# 2. Run:
python3 renewal_to_contacts.py
```

The script prints a preview table and asks for confirmation before making any changes.

---

## Expected table format

The copied table must include a header row. Column names can be in English or Dutch. The minimum required columns are **Client name**, **Client email**, and **Client phone**. Extra columns (Years, Currency, Price) are ignored.

Example (tab-separated, as copied from Apple Mail):

```
Activation date    Expiry date        Quantity  Product                                 Client name    Client email                 Client phone
10-04-2025 14:31   10-04-2026 00:00   1         Kaspersky Plus 1-Device 1 jaar (CBA)    Brilleman      a.j.brilleman@casema.nl      0302204396
11-04-2025 14:43   11-04-2026 00:00   1         F-Secure Internet Security 3-PC 1 year  van Duuren     jmj.vanduuren@gmail.com      0652344906
```

---

## Project files

```
RenewalToContacts.app        Double-click app for end users (self-contained)
renewal_to_contacts.py       Python source — all logic lives here
RenewalToContacts.applescript  AppleScript source for the app UI
build_app.sh                 Rebuilds RenewalToContacts.app from source
requirements.txt             No packages required (Python 3 + osascript, both built into macOS)
```

---

## Rebuilding the app

After any change to `renewal_to_contacts.py`:

```bash
bash build_app.sh
```

This recompiles the AppleScript and copies the updated Python script into the app bundle.

---

## Requirements

- macOS (any recent version)
- Python 3 — included with macOS; verify with `python3 --version`
- No third-party packages needed
