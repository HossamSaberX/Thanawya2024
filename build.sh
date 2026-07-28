#!/bin/bash
set -e

# Directory for storing checksums, Render caches this path
CACHE_DIR=./.render-cache
mkdir -p $CACHE_DIR

# File paths
REQS_FILE=requirements.txt
PROCESS_DATA_FILE=process_data.py
DATA_FILE=data.xlsx
REQS_CHECKSUM_FILE=$CACHE_DIR/requirements.sum
DATA_PROCESSING_CHECKSUM_FILE=$CACHE_DIR/data-processing.sum

# --- Dependency Installation ---
# Calculate the current checksum of requirements.txt
CURRENT_REQS_CHECKSUM=$(sha256sum $REQS_FILE | awk '{ print $1 }')

# Check if the checksum file exists and if the checksum has changed
if [ ! -f "$REQS_CHECKSUM_FILE" ] || [ "$(cat $REQS_CHECKSUM_FILE)" != "$CURRENT_REQS_CHECKSUM" ]; then
    echo "requirements.txt has changed, installing dependencies..."
    pip install -r $REQS_FILE
    # Store the new checksum
    echo -n "$CURRENT_REQS_CHECKSUM" > $REQS_CHECKSUM_FILE
else
    echo "requirements.txt has not changed, skipping installation."
fi

# --- Data Processing ---
# Calculate one checksum for both the importer and its source workbook
CURRENT_DATA_PROCESSING_CHECKSUM=$(sha256sum "$PROCESS_DATA_FILE" "$DATA_FILE" | sha256sum | awk '{ print $1 }')

# Regenerate whenever either the importer or source data changes
if [ ! -f "$DATA_PROCESSING_CHECKSUM_FILE" ] || [ "$(cat "$DATA_PROCESSING_CHECKSUM_FILE")" != "$CURRENT_DATA_PROCESSING_CHECKSUM" ]; then
    echo "Data source or processing code has changed, regenerating database..."
    python $PROCESS_DATA_FILE
    echo -n "$CURRENT_DATA_PROCESSING_CHECKSUM" > "$DATA_PROCESSING_CHECKSUM_FILE"
else
    echo "Data source and processing code have not changed, skipping database generation."
fi

echo "Build script finished."
