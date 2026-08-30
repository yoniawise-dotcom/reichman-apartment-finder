#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
mkdir -p vendor
if [ ! -d vendor/yad2-mcp/.git ]; then
  git clone https://github.com/Guy2co/yad2-mcp.git vendor/yad2-mcp
fi
cd vendor/yad2-mcp
npm install
npx patchright install chromium
npm run build
echo "Yad2 MCP installed in vendor/yad2-mcp"
