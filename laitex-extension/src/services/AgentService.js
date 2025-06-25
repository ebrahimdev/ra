/**
 * AgentService - Handles communication with the /agent endpoint
 */
class AgentService {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  /**
   * Sends a user request to the /agent endpoint and returns the command to execute
   * @param {string} userRequest - The user's input request
   * @returns {Promise<Object>} - The response containing the command to execute
   */
  async getCommand(userRequest) {
    // TEMPORARY: Hardcoded response for testing
    console.log('AgentService: Received request:', userRequest);

    // Simulate a small delay to mimic API call
    await new Promise(resolve => setTimeout(resolve, 500));

    return {
      command: 'ls',
      success: true
    };

    // ORIGINAL CODE (commented out for testing):
    /*
    try {
      const response = await fetch(`${this.baseUrl}/agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          request: userRequest
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Validate that the response contains a command
      if (!data.command || typeof data.command !== 'string') {
        throw new Error('Invalid response: missing or invalid command');
      }

      return {
        command: data.command,
        success: true
      };
    } catch (error) {
      return {
        command: '',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
    */
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