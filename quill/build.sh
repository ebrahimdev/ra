#!/bin/bash

# Quill Extension Build Script
# Builds, versions, packages, and installs the extension into Cursor

set -e  # Exit on any error

echo "🔨 Building Quill extension..."

# Clean previous build
echo "📁 Cleaning previous build..."
rm -rf out/
rm -f quill-*.vsix

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Bump patch version (no git tag)
echo "🔄 Bumping patch version..."
npm version patch --no-git-tag-version

# Compile TypeScript
echo "⚙️  Compiling TypeScript..."
npm run compile

# Package extension
echo "📦 Packaging extension..."
npx vsce package --allow-missing-repository

# Find the VSIX file
VSIX_FILE=$(ls quill-*.vsix | head -n 1)

if [ -z "$VSIX_FILE" ]; then
    echo "❌ No VSIX file found!"
    exit 1
fi

echo "📦 Found VSIX file: $VSIX_FILE"

# Extract extension ID from package.json
EXT_ID=$(jq -r .name package.json)

# Uninstall old version (if any)
echo "🗑️  Removing old extension ($EXT_ID) if installed..."
code --uninstall-extension "$EXT_ID" || true

# Install the new version
echo "🚀 Installing extension into Cursor..."
code --install-extension "$VSIX_FILE" --force

echo "✅ Extension built and installed successfully!"
echo "📋 Usage Tips:"
echo "   - Cmd+Shift+P → Quill: Suggest Citation"
echo "   - Cmd+Shift+C (or your shortcut) → Suggest from text"
echo "   - Developer: Reload Window in Cursor if needed"
