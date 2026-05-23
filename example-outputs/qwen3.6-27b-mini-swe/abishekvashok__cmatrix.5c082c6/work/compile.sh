#!/bin/bash
cd "$(dirname "$0")"
# Create the executable as a shell script that calls python3
cat > executable << 'PYEOF'
#!/bin/bash
exec python3 "$(dirname "$0")/cmatrix.py" "$@"
PYEOF
chmod +x executable
