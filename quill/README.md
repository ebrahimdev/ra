# Quill VS Code Extension

Quill is an intelligent research assistant that helps academic writers brainstorm, summarize, and generate structured papers directly inside VS Code.

## Features

### Manual Citation Suggestions
- Suggest citations for selected text using `Ctrl+Shift+C` (or `Cmd+Shift+C` on Mac)
- Right-click in LaTeX files to access citation suggestions

### Proactive Citation Suggestions
- **Automatic suggestions while typing** in `.tex` files
- Triggers when:
  - A complete sentence is typed (ending in `.`, `?`, `!`)
  - OR after typing 200 words since the last check
- 8-second cooldown between suggestions to prevent API overload
- Non-blocking inline notifications with "Insert" and "Dismiss" options
- Automatically inserts `\cite{key}` and updates bibliography files
- Tracks inserted citations to avoid duplicate suggestions

### Configuration
- Toggle proactive suggestions on/off via command palette or right-click menu
- Customize cooldown period and word threshold in VS Code settings
- Settings are automatically saved and persisted

## Usage

### Manual Citation Suggestions
1. Select text in a `.tex` file
2. Press `Ctrl+Shift+C` (or `Cmd+Shift+C` on Mac)
3. Or right-click and select "Quill: Suggest Citation"

### Proactive Suggestions
1. Open a `.tex` file
2. Start typing - suggestions will appear automatically
3. Click "Insert" to add the citation, or "Dismiss" to ignore

### Toggle Proactive Mode
- Use command palette: "Quill: Toggle Proactive Citation Suggestions"
- Or right-click in a `.tex` file and select the toggle option

### Configuration Options
In VS Code settings, under "Quill":
- `quill.proactiveSuggestions.enabled`: Enable/disable proactive suggestions (default: true)
- `quill.proactiveSuggestions.cooldownMs`: Cooldown period in milliseconds (default: 8000)
- `quill.proactiveSuggestions.wordThreshold`: Word count threshold (default: 200)

---
This extension is under active development.
