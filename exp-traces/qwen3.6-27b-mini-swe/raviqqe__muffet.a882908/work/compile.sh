#!/bin/bash
cd "$(dirname "$0")"
cat > executable << 'WRAPPER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/muffet.py" "$@"
WRAPPER
chmod +x executable
