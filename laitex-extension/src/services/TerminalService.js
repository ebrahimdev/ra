const vscode = require('vscode');

/**
 * TerminalService - Manages terminal operations and command execution
 */
class TerminalService {
  constructor() {
    this.terminal = null;
    this.initializeTerminal();
  }

  /**
   * Initializes a new terminal instance
   */
  initializeTerminal() {
    this.terminal = vscode.window.createTerminal('Laitex Agent Terminal');
    this.terminal.show();
  }

  /**
   * Executes a command in the terminal
   * @param {string} command - The command to execute
   * @returns {Promise<Object>} - The result of the command execution
   */
  async executeCommand(command) {
    try {
      if (!this.terminal) {
        this.initializeTerminal();
      }

      // Ensure terminal is visible
      this.terminal.show();

      // Send the command to the terminal
      this.terminal.sendText(command);

      return {
        success: true,
        output: `Command "${command}" sent to terminal successfully.`
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  /**
   * Clears the terminal
   */
  clearTerminal() {
    if (this.terminal) {
      this.terminal.sendText('clear');
    }
  }

  /**
   * Closes the terminal
   */
  closeTerminal() {
    if (this.terminal) {
      this.terminal.dispose();
      this.terminal = null;
    }
  }

  /**
   * Gets the current terminal instance
   * @returns {vscode.Terminal|null} - The current terminal instance
   */
  getTerminal() {
    return this.terminal;
  }

  /**
   * Checks if the terminal is active
   * @returns {boolean} - True if terminal is active, false otherwise
   */
  isTerminalActive() {
    return this.terminal !== null;
  }
}

module.exports = TerminalService; 