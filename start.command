#!/bin/bash
# Double-click to preview In My Backyard at http://localhost:8767
cd "$(dirname "$0")"
open "http://localhost:8767" 2>/dev/null
python3 -m http.server 8767
