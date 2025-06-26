/**
 * AgentService - Handles communication with the /agent endpoint
 */
class AgentService {
  constructor(baseUrl = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
  }

  /**
   * Sends a user request to the /agent endpoint and returns the response
   * @param {string} userRequest - The user's input request
   * @param {Array} chatHistory - Optional chat history
   * @returns {Promise<Object>} - The response from the agent
   */
  async getCommand(userRequest, chatHistory = []) {
    try {
      console.log('AgentService: Sending request to agent:', userRequest);

      const response = await fetch(`${this.baseUrl}/agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: userRequest,
          chat_history: chatHistory
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Agent processing failed');
      }

      // Check if the response contains tool calls that need execution
      if (data.tool_calls && data.tool_calls.length > 0) {
        return {
          success: true,
          response: data.response,
          tool_calls: data.tool_calls,
          needs_tool_execution: true
        };
      }

      return {
        success: true,
        response: data.response,
        tool_calls: data.tool_calls || []
      };
    } catch (error) {
      console.error('AgentService error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  /**
   * Sends a context-aware request to the /agent/inline endpoint
   * @param {Object} request - The request object with context
   * @returns {Promise<Object>} - The response from the agent
   */
  async getCommandWithContext(request) {
    try {
      console.log('AgentService: Sending context-aware request:', request);

      const response = await fetch(`${this.baseUrl}/agent/inline`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Agent processing failed');
      }

      return {
        success: true,
        response: data.response,
        tool_calls: data.tool_calls || []
      };
    } catch (error) {
      console.error('AgentService context error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  /**
   * Execute a tool and return the result to the agent
   * @param {string} toolName - Name of the tool
   * @param {Object} toolInput - Input for the tool
   * @returns {Promise<Object>} - The result from tool execution
   */
  async executeTool(toolName, toolInput) {
    try {
      const response = await fetch(`${this.baseUrl}/agent/tool_execution`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tool_name: toolName,
          tool_input: toolInput
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Tool execution error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }

  /**
   * Get available tools from the agent
   * @returns {Promise<Object>} - List of available tools
   */
  async getAvailableTools() {
    try {
      const response = await fetch(`${this.baseUrl}/agent/tools`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching tools:', error);
      return { tools: [] };
    }
  }

  /**
   * Updates the base URL for the agent service
   * @param {string} newBaseUrl - The new base URL
   */
  setBaseUrl(newBaseUrl) {
    this.baseUrl = newBaseUrl;
  }

  /**
   * Gets the current base URL
   * @returns {string} - The current base URL
   */
  getBaseUrl() {
    return this.baseUrl;
  }
}

module.exports = AgentService; 