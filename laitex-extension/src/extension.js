const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
const AgentService = require("./services/AgentService");
const TerminalService = require("./services/TerminalService");
const InlineChatProvider = require("./InlineChatProvider");

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
    this.chatHistory = []; // Store chat history for the agent
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

      // Get response from agent service
      const agentResponse = await this.agentService.getCommand(message, this.chatHistory);

      if (agentResponse.success) {
        // Remove loading message
        this.removeLastMessage();

        // Add agent response to chat
        this.addMessageToChat('assistant', agentResponse.response);

        // Update chat history
        this.chatHistory.push({
          user: message,
          assistant: agentResponse.response
        });

        // Handle tool execution if needed
        if (agentResponse.needs_tool_execution && agentResponse.tool_calls) {
          await this.handleToolExecution(agentResponse.tool_calls);
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

  async handleToolExecution(toolCalls) {
    for (const toolCall of toolCalls) {
      try {
        const [action, input] = toolCall;

        if (action.tool === 'terminal_command') {
          // Execute terminal command
          const command = input.command;
          this.addMessageToChat('system', `🔧 Executing command: \`${command}\``);

          const terminalResult = await this.terminalService.executeCommand(command);

          if (terminalResult.success) {
            this.addMessageToChat('system', `✅ Command executed successfully.`);

            // Send tool execution result back to agent
            await this.agentService.executeTool('terminal_command', {
              command: command,
              output: terminalResult.output,
              success: true
            });
          } else {
            this.addMessageToChat('system', `❌ Command failed: ${terminalResult.error}`);

            // Send error result back to agent
            await this.agentService.executeTool('terminal_command', {
              command: command,
              output: terminalResult.error,
              success: false
            });
          }
        } else if (action.tool === 'rag_search') {
          // RAG search is handled on the server side, just show info
          this.addMessageToChat('system', `🔍 Searching knowledge base for: "${input.query}"`);
        }
      } catch (error) {
        this.addMessageToChat('system', `❌ Tool execution error: ${error.message}`);
      }
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
    this.chatHistory = []; // Clear chat history
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
  const inlineChatProvider = new InlineChatProvider(context, agentService);

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

  // Register the inline chat command
  let inlineChatDisposable = vscode.commands.registerCommand("laitex.inlineChat", function () {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      inlineChatProvider.showInlineChat(editor);
    }
  });
  context.subscriptions.push(inlineChatDisposable);

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