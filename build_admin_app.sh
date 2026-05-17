#!/bin/bash
# build_admin_app.sh — compiles AdminToContacts.app from source
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/AdminToContacts.app"

echo "Building $APP ..."

# Remove old build if present
rm -rf "$APP"

# Compile AppleScript → .app bundle
osacompile -o "$APP" "$DIR/AdminToContacts.applescript"

# Bundle the Python script inside the app's Resources folder
cp "$DIR/admin_to_contacts.py" "$APP/Contents/Resources/"

echo ""
echo "Done.  $APP is ready."
echo ""
echo "Usage:"
echo "  1. Copy the admin table (Cmd+C)"
echo "  2. Double-click AdminToContacts.app"
