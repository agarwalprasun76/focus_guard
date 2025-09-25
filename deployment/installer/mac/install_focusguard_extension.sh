#!/bin/bash
set -e

# Copy native host
mkdir -p ~/Library/Application\ Support/FocusGuard
cp focusguard_native_host ~/Library/Application\ Support/FocusGuard/

# Copy extension files
mkdir -p ~/Library/Application\ Support/FocusGuard/ext
cp manifest.json background.js icons/* ~/Library/Application\ Support/FocusGuard/ext/

# Write the native messaging plist
cat > ~/Library/Google/Chrome/NativeMessagingHosts/com.focusguard.native.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Name</key>
    <string>com.focusguard.native</string>
    <key>Description</key>
    <string>FocusGuard Native Host</string>
    <key>Path</key>
    <string>/Users/$USER/Library/Application Support/FocusGuard/focusguard_native_host</string>
    <key>Type</key>
    <string>stdio</string>
    <key>Allowed-origins</key>
    <array>
        <string>chrome-extension://YOUR_EXTENSION_ID/</string>
    </array>
</dict>
</plist>
EOF