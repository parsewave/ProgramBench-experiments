#!/bin/sh
chmod +x $0
WORKDIR=$(dirname $0)
go build -o executable $WORKDIR/main.go
