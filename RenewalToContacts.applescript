-- RenewalToContacts.applescript
--
-- Double-click this app after copying the renewal table in Apple Mail (Cmd+C).
-- It will show a preview dialog and import the clients into Apple Contacts.

on run
    -- ── Locate the Python script bundled inside this .app ─────────────────
    set appPosixPath to POSIX path of (path to me)
    set scriptPath to appPosixPath & "Contents/Resources/renewal_to_contacts.py"

    -- ── Verify the script exists ──────────────────────────────────────────
    try
        do shell script "test -f " & quoted form of scriptPath
    on error
        display dialog "renewal_to_contacts.py was not found inside the app bundle." & return & return & scriptPath buttons {"OK"} default button "OK" with title "Renewal Import" with icon stop
        return
    end try

    -- ── Python command: covers Intel Homebrew, Apple Silicon Homebrew, system ──
    set py to "export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:$PATH && python3"

    -- ── Parse clipboard and get preview ──────────────────────────────────
    try
        set previewText to do shell script py & " " & quoted form of scriptPath & " --list"
    on error errMsg
        display dialog errMsg buttons {"OK"} default button "OK" with title "Renewal Import" with icon stop
        return
    end try

    -- ── Confirmation dialog ───────────────────────────────────────────────
    set dlg to display dialog previewText & return & return & "Import into Apple Contacts?" buttons {"Cancel", "Import"} default button "Import" with title "Renewal Import"

    if button returned of dlg is "Import" then
        -- ── Run import ────────────────────────────────────────────────────
        try
            with timeout of 300 seconds
                set importResult to do shell script py & " " & quoted form of scriptPath & " --import"
            end timeout
            display dialog importResult buttons {"Done"} default button "Done" with title "Import Complete"
        on error errMsg
            display dialog errMsg buttons {"OK"} default button "OK" with title "Import Error" with icon stop
        end try
    end if
    tell me to quit
end run
