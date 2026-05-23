#!/bin/sh
set -e
cd "$(dirname "$0")"
cc -O2 -o executable cmatrix.c
