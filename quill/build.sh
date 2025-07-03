#!/bin/bash

# Quill Extension Build Script
# This script builds the extension and installs it into Cursor

set -e  # Exit on any error

echo "🔨 Building Quill extension..."

# Clean previous build
echo "📁 Cleaning previous build..."
rm -rf out/
rm -f quill-*.vsix

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Compile TypeScript
echo "⚙️  Compiling TypeScript..."
npm run compile

# Package extension
echo "📦 Packaging extension..."
npx vsce package --allow-missing-repository

# Find the generated VSIX file
VSIX_FILE=$(ls quill-*.vsix | head -n 1)

if [ -z "$VSIX_FILE" ]; then
    echo "❌ No VSIX file found!"
    exit 1
fi

echo "📦 Found VSIX file: $VSIX_FILE"

# Force install the extension
echo "🚀 Installing extension into Cursor..."
code --install-extension "$VSIX_FILE" --force

echo "✅ Extension built and installed successfully!"
echo "📋 You can now use the extension in Cursor:"
echo "   - Cmd+Shift+C: Suggest Citation (in LaTeX files)"
echo "   - Cmd+Shift+P → 'Quill: Hello World'"
echo "   - Cmd+Shift+P → 'Quill: Suggest Citation'" 