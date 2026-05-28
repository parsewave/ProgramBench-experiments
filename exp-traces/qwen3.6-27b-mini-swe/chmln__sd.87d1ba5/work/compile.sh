#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

# Copy the implementation as the executable with proper shebang
# The executable can just be the Python script itself
cp "$DIR/sd_impl.py" "$DIR/executable"
chmod +x "$DIR/executable"
