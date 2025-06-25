# Laitex Extension - Modular Code Execution Agent

A VS Code extension that provides a modular code execution agent system. Users can describe what they want to do in natural language, and the agent will generate and execute the appropriate terminal commands.

## Architecture

The extension is built with a modular architecture consisting of the following components:

### Core Services

#### 1. AgentService (`src/services/AgentService.js`)
- **Purpose**: Handles communication with the `/agent` endpoint
- **Key Methods**:
  - `getCommand(userRequest)`: Sends user request to agent endpoint and returns command
  - `setBaseUrl(newBaseUrl)`: Updates the base URL for the agent service
  - `getBaseUrl()`: Gets the current base URL

#### 2. TerminalService (`src/services/TerminalService.js`)
- **Purpose**: Manages terminal operations and command execution
- **Key Methods**:
  - `executeCommand(command)`: Executes a command in the VS Code terminal
  - `clearTerminal()`: Clears the terminal
  - `closeTerminal()`: Closes the terminal
  - `isTerminalActive()`: Checks if terminal is active

### UI Components

#### 3. LaitexChatViewProvider (`src/extension.js`)
- **Purpose**: Manages the chat interface and orchestrates the workflow
- **Key Features**:
  - Handles user messages from the webview
  - Coordinates between AgentService and TerminalService
  - Manages chat state and UI updates

#### 4. Webview Interface (`media/webview.html` & `media/webview.js`)
- **Purpose**: Provides the chat interface for user interaction
- **Features**:
  - Real-time chat interface
  - Message history
  - Clear chat functionality
  - Responsive design

## Workflow

1. **User Input**: User types a request in the chat interface
2. **Agent Processing**: Request is sent to the `/agent` endpoint via AgentService
3. **Command Generation**: Agent returns a command to execute
4. **Terminal Execution**: Command is executed in VS Code terminal via TerminalService
5. **Feedback**: User receives confirmation of command execution

## Setup

### Prerequisites
- VS Code extension development environment
- FastAPI server with `/agent` endpoint (to be implemented)

### Installation
1. Clone the repository
2. Install dependencies: `npm install`
3. Build the extension: `npm run build`
4. Package the extension: `npm run package`

### Configuration
The AgentService can be configured with a custom base URL:
```javascript
const agentService = new AgentService('http://your-server:8000');
```

## API Requirements

The `/agent` endpoint should accept POST requests with the following format:

**Request:**
```json
{
  "request": "user's natural language request"
}
```

**Response:**
```json
{
  "command": "terminal command to execute",
  "success": true
}
```

## File Structure

```
laitex-extension/
├── src/
│   ├── extension.js              # Main extension entry point
│   └── services/
│       ├── AgentService.js       # Agent communication service
│       └── TerminalService.js    # Terminal management service
├── media/
│   ├── webview.html             # Chat interface HTML
│   ├── webview.js               # Chat interface JavaScript
│   └── icon.svg                 # Extension icon
├── dist/
│   └── extension.js             # Compiled extension
├── package.json                 # Extension manifest
└── README.md                    # This file
```

## Development

### Adding New Features
1. Create new service modules in `src/services/`
2. Update the main extension to use new services
3. Modify webview interface as needed
4. Test thoroughly before deployment

### Testing
- Test agent communication with mock server
- Verify terminal command execution
- Test error handling scenarios
- Validate UI responsiveness

## Security Considerations

- Commands are executed in the user's terminal - ensure proper validation
- Agent endpoint should validate and sanitize requests
- Consider implementing command whitelisting for production use

## Contributing

1. Follow the modular architecture pattern
2. Add proper error handling
3. Include JSDoc comments for all public methods
4. Test thoroughly before submitting changes

## License

[Add your license information here] 