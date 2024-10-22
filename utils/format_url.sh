#!/bin/bash

function format_url()
{
    local url="${1}"

    # Extract the file extension
    local file_extension="${url##*.}"

    # Check if the extension is 'zip'    
    if [ "$file_extension" == "zip" ]; then
        # Replace '/d/' with '/v/' and return the parsed URL
        echo "${url//\/d\//\/v\/}"
    else
        # If not a zip file, return the original URL
        echo "$url"
    fi
}
