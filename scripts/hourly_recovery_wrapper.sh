#!/bin/bash

# Wrapper script for hourly recovery driver that handles missing environment variables
# This logs locally when Paperclip API is not available

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/tmp/hourly_recovery"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if Paperclip environment is set
if [[ -z "$PAPERCLIP_API_KEY" ]]; then
    # Log the issue but continue with the driver
    echo "$(date '+%Y-%m-%dT%H:%M:%S+00:00') [WRAPPER] PAPERCLIP_API_KEY not set - logging locally instead" >> "$LOG_DIR/wrapper.log"

    # Set a placeholder API key to avoid crashing the driver
    export PAPERCLIP_API_KEY="placeholder"
    export PAPERCLIP_API_URL="http://localhost:3000"
fi

# Run the hourly recovery driver
cd "$SCRIPT_DIR"
python3 scripts/hourly_recovery_driver.py >> "$LOG_DIR/driver.log" 2>&1

# Check if the driver failed due to API key issues
if grep -q "PAPERCLIP_API_KEY not set" "$LOG_DIR/driver.log" && [[ "$PAPERCLIP_API_KEY" == "placeholder" ]]; then
    # Extract the latest comment that would have been posted
    LAST_RUN_LOG="$LOG_DIR/driver.log"
    if [[ -f "$LAST_RUN_LOG" ]]; then
        # Get the most recent comment body (this is a simplified extraction)
        COMMENT=$(grep -A 20 "Real rows:" "$LAST_RUN_LOG" | tail -n +2 | head -n -1)
        echo "" >> "$LOG_DIR/local_comments.log"
        echo "$(date '+%Y-%m-%dT%H:%M:%S+00:00')" >> "$LOG_DIR/local_comments.log"
        echo "COMMENT THAT WOULD HAVE BEEN POSTED:" >> "$LOG_DIR/local_comments.log"
        echo "$COMMENT" >> "$LOG_DIR/local_comments.log"
        echo "" >> "$LOG_DIR/local_comments.log"
    fi
fi

echo "$(date '+%Y-%m-%dT%H:%M:%S+00:00') [WRAPPER] Hourly recovery driver completed" >> "$LOG_DIR/wrapper.log"