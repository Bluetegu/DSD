#!/bin/bash
# build_app.sh — compiles RenewalToContacts.app from source
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/RenewalToContacts.app"

echo "Building $APP ..."

# Remove old build if present
rm -rf "$APP"

# Compile AppleScript → .app bundle
osacompile -o "$APP" "$DIR/RenewalToContacts.applescript"

# Bundle the Python script inside the app's Resources folder
cp "$DIR/renewal_to_contacts.py" "$APP/Contents/Resources/"

echo ""
echo "Done.  $APP is ready."
echo ""
echo "Usage:"
echo "  1. In Apple Mail: select the renewal table → Cmd+C"
echo "  2. Double-click RenewalToContacts.app"
