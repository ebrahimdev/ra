const vscode = require("vscode");
const AgentService = require("./services/AgentService");

class InlineChatProvider {
  constructor(context, agentService) {
    this.context = context;
    this.agentService = agentService;
    this.currentChat = null;
  }

  async showInlineChat(editor) {
    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);

    if (!selectedText.trim()) {
      vscode.window.showInformationMessage("Please select some text to start an inline chat.");
      return;
    }

    // Create a decoration for the selected text
    const decorationType = vscode.window.createTextEditorDecorationType({
      backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
      border: '1px solid #007acc',
      borderRadius: '3px'
    });

    // Apply decoration to selected text
    editor.setDecorations(decorationType, [selection]);

    // Create input box for the chat
    const userInput = await vscode.window.showInputBox({
      placeHolder: "Ask about the selected text...",
      prompt: `Selected text: "${selectedText.substring(0, 50)}${selectedText.length > 50 ? '...' : ''}"`,
      ignoreFocusOut: true
    });

    // Clear decoration
    decorationType.dispose();

    if (!userInput) {
      return;
    }

    // Show progress
    await vscode.window.withProgress({
      location: vscode.ProgressLocation.Notification,
      title: "Laitex Assistant",
      cancellable: false
    }, async (progress) => {
      progress.report({ message: "Processing your request..." });

      try {
        // Get document context
        const document = editor.document;
        const documentText = document.getText();
        const lineNumber = selection.start.line;

        // Get surrounding context (a few lines before and after)
        const contextStart = Math.max(0, lineNumber - 3);
        const contextEnd = Math.min(document.lineCount - 1, lineNumber + 3);
        const contextLines = [];

        for (let i = contextStart; i <= contextEnd; i++) {
          contextLines.push(document.lineAt(i).text);
        }

        const context = contextLines.join('\n');

        // Prepare the request with context
        const request = {
          user_input: userInput,
          selected_text: selectedText,
          document_context: context,
          document_path: document.fileName,
          line_number: lineNumber,
          chat_history: []
        };

        // Send to agent
        const response = await this.agentService.getCommandWithContext(request);

        if (response.success) {
          // Show the response in a notification
          const action = await vscode.window.showInformationMessage(
            response.response,
            "Copy to Clipboard",
            "Insert Above",
            "Replace Selection"
          );

          if (action === "Copy to Clipboard") {
            await vscode.env.clipboard.writeText(response.response);
          } else if (action === "Insert Above") {
            await this.insertTextAbove(editor, selection, response.response);
          } else if (action === "Replace Selection") {
            await this.replaceSelection(editor, selection, response.response);
          }
        } else {
          vscode.window.showErrorMessage(`Error: ${response.error}`);
        }

      } catch (error) {
        vscode.window.showErrorMessage(`Unexpected error: ${error.message}`);
      }
    });
  }

  async insertTextAbove(editor, selection, text) {
    const position = new vscode.Position(selection.start.line, 0);
    await editor.edit(editBuilder => {
      editBuilder.insert(position, text + '\n');
    });
  }

  async replaceSelection(editor, selection, text) {
    await editor.edit(editBuilder => {
      editBuilder.replace(selection, text);
    });
  }
}

module.exports = InlineChatProvider; 