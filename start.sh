#!/bin/bash

# Constants
readonly FILE='URLs.txt'
readonly SESSION_LOG='session_log.txt'
readonly SCRIPTS_DIR='utils'

# Clear the session log file_name
: > "$SESSION_LOG"

# Import all functions in utils directory
for script in "$SCRIPTS_DIR"/*.sh; do
    source "$script"
done

while read -r line; do
    # Format the input URL if the file is a .zip
    formatted_url=$(format_url "$line")

    # Download Bunkr album
    python3 downloader.py "$formatted_url"
done < "$FILE"

# Clear the URLs file
: > "$FILE"
