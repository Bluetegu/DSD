# DSD Contacts Import Tools

Two macOS apps that import client tables copied from Apple Mail or a browser into Apple Contacts. No technical knowledge required — just copy, double-click, and confirm.

> **Disclaimer**  
> This software is provided as-is, without any warranty. It directly modifies data in Apple Contacts. Always make sure you have a backup of your contacts (e.g. via iCloud or an exported `.vcf` file) before running an import. The authors accept no responsibility for data loss, incorrect data, or any other damage resulting from the use of this software.

---

## Download

1. Go to the [**Releases**](https://github.com/Bluetegu/DSD/releases) page
2. Under the latest release, download **AdminToContacts.zip** and/or **RenewalToContacts.zip**
3. Unzip and move the app to wherever you like (e.g. your Desktop or Applications folder)

**First launch — "damaged file" warning:**  
macOS may block apps downloaded from the internet. If you see a "damaged" error, open Terminal and run:
```bash
xattr -cr ~/Downloads/AdminToContacts.app
```
Replace `~/Downloads/` with wherever you saved the app. After that, double-click works normally.

---

## Apps

| App                       | Source               | What it imports                                                             |
| ------------------------- | -------------------- | --------------------------------------------------------------------------- |
| **RenewalToContacts.app** | Renewal email table  | Client name, email, phone; renewal details in Note                          |
| **AdminToContacts.app**   | Administration table | Company, contact name (split), address (home), email; admin details in Note |

---

## RenewalToContacts

### How it works

| Contact field | Source column                                   |
| ------------- | ----------------------------------------------- |
| Last Name     | Client name                                     |
| Email         | Client email                                    |
| Phone         | Client phone                                    |
| Note          | Activation date, Expiry date, Quantity, Product |

**Matching logic**
- Existing contact (matched by email) → Note is **prepended** to any existing note (history preserved); phone is added if none is present.
- No match → new contact is created.

### Usage (App)

1. Open the renewal email in **Apple Mail**.
2. Select the entire table and copy it — **Cmd+C**.
3. Double-click **`RenewalToContacts.app`**.
4. A dialog shows the list of clients found. Review it.
5. Click **Import** to write them to Apple Contacts.
6. A confirmation dialog reports how many were created and updated.

### Usage (Terminal — advanced)

```bash
# 1. Copy the table in Apple Mail (Cmd+C)
# 2. Run:
python3 renewal_to_contacts.py
```

### Expected table format

Column names can be in English or Dutch. Minimum required columns: **Client name**, **Client email**, **Client phone**. Extra columns are ignored.

```
Activation date    Expiry date        Quantity  Product                                 Client name    Client email               Client phone
10-04-2025 14:31   10-04-2026 00:00   1         Kaspersky Plus 1-Device 1 jaar (CBA)    Janxxxx        j.janxxx@example.nl        0301234567
11-04-2025 14:43   11-04-2026 00:00   1         F-Secure Internet Security 3-PC 1 year  de Vyyy        m.dyyyy@example.com        0612345678
```

---

## AdminToContacts

### How it works

| Contact field | Source column                            |
| ------------- | ---------------------------------------- |
| First Name    | First word of Contact person             |
| Last Name     | Remainder of Contact person              |
| Company       | Company name                             |
| Email         | Email (label: work)                      |
| Address       | Address + Postal code/City (label: home) |
| Note          | Company, address, and postal/city        |

**Matching logic**
- Existing contact (matched by email) → company, note, and address fields are **updated**. If an address already exists, its street/zip/city are updated in place; if not, a new home address is added. If the contact has no first name (e.g. created by RenewalToContacts), first and last name are filled in.
- Note is **prepended** to any existing note, so previous import history is preserved.
- No match → new contact is created with all available fields.
- Cells containing `n/a`, `n.a.`, `-`, `nvt`, or `n.v.t.` are treated as empty.

### Usage (App)

1. Open the administration table in **Apple Mail** or your browser.
2. Select the entire table and copy it — **Cmd+C**.
3. Double-click **`AdminToContacts.app`**.
4. A dialog shows the list of contacts found. Review it.
5. Click **Import** to write them to Apple Contacts.
6. A confirmation dialog reports how many were created and updated.

### Usage (Terminal — advanced)

```bash
# 1. Copy the table (Cmd+C)
# 2. Run:
python3 admin_to_contacts.py
```

### Expected table format

Column names can be in English or Dutch. Required columns: **Company name**, **Contact person**, **Email**. Address columns (**Address**, **Postal code/City**) are optional.

```
Company name          Contact person     Address              Postal code/City    Email
Acme Solutions BV     Jan de Vries       Hoofdstraat 12       1234AB / Amsterdam  j.devries@acme-example.nl
n/a                   Maria Bakker       -                    -                   m.bakker@example.com
```

---

## Project files

```
RenewalToContacts.app          Double-click app — renewal imports
AdminToContacts.app            Double-click app — admin imports
renewal_to_contacts.py         Python source for renewal import
admin_to_contacts.py           Python source for admin import
RenewalToContacts.applescript  AppleScript UI for renewal app
AdminToContacts.applescript    AppleScript UI for admin app
build_app.sh                   Rebuilds RenewalToContacts.app
build_admin_app.sh             Rebuilds AdminToContacts.app
renewal-example.txt            Example renewal table (tab-separated)
admin-example.txt              Example admin table (tab-separated)
requirements.txt               No packages required
```

---

## Rebuilding the apps

After any change to the Python source:

```bash
bash build_app.sh          # rebuilds RenewalToContacts.app
bash build_admin_app.sh    # rebuilds AdminToContacts.app
```

> **Sharing the app with others**  
> Before sending the app (zip, AirDrop, etc.), run this once in Terminal to prevent a "damaged file" error on the recipient's Mac:
> ```bash
> xattr -cr AdminToContacts.app
> xattr -cr RenewalToContacts.app
> ```
> If the recipient already has the app and sees the error, they can run:
> ```bash
> xattr -cr ~/Downloads/AdminToContacts.app
> ```
> After that, double-click works normally. The build scripts (`build_admin_app.sh`, `build_app.sh`) already run this automatically.

---

## Requirements

- macOS (any recent version)
- Python 3 — included with macOS; verify with `python3 --version`
- No third-party packages needed

---

## License

This software is released into the public domain under the [Unlicense](LICENSE).  
You are free to use, copy, modify, and distribute it for any purpose, without restrictions.

---

## Credits

Developed with the help of [GitHub Copilot](https://github.com/features/copilot).
