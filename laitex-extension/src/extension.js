const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
const AgentService = require("./services/AgentService");
const TerminalService = require("./services/TerminalService");

function getWebviewContent(webviewContainer, context) {
  const htmlPath = path.join(context.extensionPath, "media", "webview.html");
  let html = fs.readFileSync(htmlPath, "utf8");

  const scriptPath = vscode.Uri.file(
    path.join(context.extensionPath, "media", "webview.js")
  );
  const scriptUri = webviewContainer.webview.asWebviewUri(scriptPath);

  html = html.replace(
    `<script src="webview.js"></script>`,
    `<script src="${scriptUri}"></script>`
  );

  return html;
}

class LaitexChatViewProvider {
  constructor(context, agentService, terminalService) {
    this.context = context;
    this.agentService = agentService;
    this.terminalService = terminalService;
  }

  resolveWebviewView(webviewView) {
    this.webviewView = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = getWebviewContent(webviewView, this.context);

    // Handle messages from the webview
    webviewView.webview.onDidReceiveMessage(async (data) => {
      switch (data.type) {
        case 'sendMessage':
          await this.handleUserMessage(data.message);
          break;
        case 'clearChat':
          this.clearChat();
          break;
      }
    });
  }

  async handleUserMessage(message) {
    try {
      // Add user message to chat
      this.addMessageToChat('user', message);

      // Show loading indicator
      this.addMessageToChat('assistant', 'Processing your request...', true);

      // Get command from agent service
      const agentResponse = await this.agentService.getCommand(message);

      if (agentResponse.success) {
        // Remove loading message and add success message
        this.removeLastMessage();
        this.addMessageToChat('assistant', `Command generated: \`${agentResponse.command}\``);

        // Execute command in terminal
        const terminalResult = await this.terminalService.executeCommand(agentResponse.command);

        if (terminalResult.success) {
          this.addMessageToChat('system', `✅ Command executed successfully in terminal.`);
        } else {
          this.addMessageToChat('system', `❌ Failed to execute command: ${terminalResult.error}`);
        }
      } else {
        // Remove loading message and add error message
        this.removeLastMessage();
        this.addMessageToChat('assistant', `❌ Error: ${agentResponse.error}`);
      }
    } catch (error) {
      this.removeLastMessage();
      this.addMessageToChat('assistant', `❌ Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  addMessageToChat(sender, message, isLoading = false) {
    if (this.webviewView) {
      this.webviewView.webview.postMessage({
        type: 'addMessage',
        sender,
        message,
        isLoading
      });
    }
  }

  removeLastMessage() {
    if (this.webviewView) {
      this.webviewView.webview.postMessage({
        type: 'removeLastMessage'
      });
    }
  }

  clearChat() {
    if (this.webviewView) {
      this.webviewView.webview.postMessage({
        type: 'clearChat'
      });
    }
  }
}

function activate(context) {
  console.log('Laitex extension is now active!');

  // Initialize services
  const agentService = new AgentService();
  const terminalService = new TerminalService();

  // Register the command for the old panel (optional, can remove if not needed)
  let disposable = vscode.commands.registerCommand("laitex.openChat", function () {
    const panel = vscode.window.createWebviewPanel(
      "laitexChat",
      "Laitex Assistant",
      vscode.ViewColumn.Beside,
      {
        enableScripts: true
      }
    );
    panel.webview.html = getWebviewContent(panel, context);
  });
  context.subscriptions.push(disposable);

  // Register the new WebviewViewProvider for the sidebar/panel
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'laitexChatView',
      new LaitexChatViewProvider(context, agentService, terminalService)
    )
  );
}

function deactivate() { }

module.exports = {
  activate,
  deactivate,
}; 