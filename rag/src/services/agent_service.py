"""
Agent service for the RAG server.
"""
import logging
import json
import requests
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent, create_structured_chat_agent
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import BaseModel, Field

from ..config import LLM_URL, AGENT_TEMPERATURE, AGENT_N_PREDICT, LLM_STOP_TOKENS

logger = logging.getLogger(__name__)

class LlamaCppChat(BaseChatModel):
    """
    LangChain-compatible chat model for llama.cpp HTTP endpoint.
    Implements the required methods for use with create_openai_functions_agent.
    """
    model: str = "llama.cpp"
    temperature: float = AGENT_TEMPERATURE
    n_predict: int = AGENT_N_PREDICT
    stop: Optional[list] = LLM_STOP_TOKENS
    endpoint_url: str = LLM_URL

    def _convert_messages(self, messages: List[Any]) -> str:
        # Start with a clear system message to reset context
        prompt = "You are a helpful AI coding assistant. You help users with development tasks and can execute terminal commands when needed.\n\n"
        
        # Add conversation history
        for message in messages:
            if hasattr(message, "type"):
                mtype = message.type
                content = message.content
            else:
                mtype = message.get("type")
                content = message.get("content")
            
            if mtype == "human":
                prompt += f"User: {content}\n"
            elif mtype == "ai":
                prompt += f"Assistant: {content}\n"
            elif mtype == "system":
                # Skip system messages as we already have the system prompt
                continue
        
        # Add the final user message if it's not already there
        if messages and hasattr(messages[-1], "type") and messages[-1].type == "human":
            prompt += "Assistant: "
        elif messages and messages[-1].get("type") == "human":
            prompt += "Assistant: "
        else:
            prompt += "Assistant: "
            
        return prompt

    def _call(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        prompt = self._convert_messages(messages)
        
        # Debug: Print the prompt being sent
        print(f"=== PROMPT SENT TO LLAMA.CPP ===")
        print(prompt)
        print("=== END PROMPT ===")
        
        response = requests.post(self.endpoint_url, json={
            "prompt": prompt,
            "temperature": self.temperature,
            "n_predict": self.n_predict,
            "stream": False,
            "stop": self.stop
        })
        
        content = response.json().get("content", "")
        print(f"=== RESPONSE FROM LLAMA.CPP ===")
        print(content)
        print("=== END RESPONSE ===")
        
        return content

    def invoke(self, input, **kwargs):
        # input is a dict with 'messages' key (list of messages)
        messages = input["messages"] if isinstance(input, dict) and "messages" in input else input
        content = self._call(messages, **kwargs)
        return AIMessage(content=content)

    def bind(self, **kwargs):
        # For LangChain compatibility (returns a copy with updated params)
        params = self.dict()
        params.update(kwargs)
        return LlamaCppChat(**params)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        content = self._call(messages, stop=stop or self.stop)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @property
    def _llm_type(self) -> str:
        return "llama.cpp"

class TerminalTool(BaseTool):
    """Tool for executing terminal commands on the user's machine"""
    
    name: str = "terminal_command"
    description: str = "Execute a terminal command on the user's machine. Use this for file operations, running scripts, git commands, etc."
    
    class InputSchema(BaseModel):
        command: str = Field(description="The terminal command to execute")
    
    def _run(self, command: str) -> str:
        """This will be called by the VS Code extension, not directly"""
        # Return a special format that the extension can recognize
        return json.dumps({
            "tool": "terminal_command",
            "command": command,
            "needs_execution": True
        })
    
    async def _arun(self, command: str) -> str:
        return self._run(command)

class RAGSearchTool(BaseTool):
    """Tool for searching the RAG knowledge base"""
    
    name: str = "rag_search"
    description: str = "Search the knowledge base of academic papers for relevant information"
    vector_store: Optional[Any] = None
    
    class InputSchema(BaseModel):
        query: str = Field(description="The search query")
        k: int = Field(default=5, description="Number of results to return")
    
    def _run(self, query: str, k: int = 5) -> str:
        """Execute the search tool."""
        try:
            # Create semantic query
            semantic_query = self._create_semantic_query(query)
            
            # Determine which collection to search based on query type
            # Use fine chunks for citation-related queries, coarse for general questions
            if any(word in query.lower() for word in ['cite', 'citation', 'reference', 'quote']):
                # Use fine chunks for citation suggestions
                results = self.vector_store.search_collection(semantic_query, k, "fine")
            else:
                # Use coarse chunks for general question answering
                results = self.vector_store.search_collection(semantic_query, k, "coarse")
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"Error in RAG search tool: {e}")
            return f"Error searching knowledge base: {str(e)}"
    
    def _create_semantic_query(self, user_question: str) -> str:
        """Create a semantic query using the LLM"""
        prompt = f"""You are a research assistant helping users retrieve the most relevant content from a vector database of academic paper chunks.

Given a user question, rewrite it into a clear, specific, and semantically rich query suitable for embedding and similarity-based retrieval.

User Question:
{user_question}

Rewritten Semantic Search Query:"""

        try:
            response = requests.post(LLM_URL, json={
                "prompt": prompt,
                "temperature": 0.3,
                "n_predict": 100,
                "stream": False,
                "stop": ["\nUser:", "\nAssistant:", "\n\n"]
            })
            rewritten_query = response.json().get("content", "").strip()
            
            return rewritten_query if rewritten_query else user_question
        except Exception:
            return user_question
    
    def _format_search_results(self, results: Dict[str, Any]) -> str:
        """Format search results for the agent"""
        if not results.get("results"):
            return "No relevant results found in the knowledge base."
        
        formatted_results = []
        for i, result in enumerate(results["results"], 1):
            formatted_results.append(f"Result {i}:\n{result['text']}\n")
        
        return "\n".join(formatted_results)
    
    async def _arun(self, query: str, k: int = 5) -> str:
        return self._run(query, k)

class AgentService:
    """Main agent service that orchestrates the LangChain agent"""
    
    def __init__(self, vector_store=None):
        """Initialize the agent service with tools and LLM."""
        self.llm = LlamaCppChat()
        self.vector_store = vector_store
        
        # Create tools with vector store service
        rag_tool = RAGSearchTool()
        rag_tool.vector_store = self.vector_store
        self.tools = [
            TerminalTool(), 
            rag_tool
        ]
        
        # Create the agent
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)
        
        logger.info("Agent service initialized successfully")
    
    def _create_agent(self):
        """Create the LangChain agent."""
        # Define the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI coding assistant. You can help users with development tasks and have access to various tools.

Available tools:
- terminal_command: Execute terminal commands on the user's machine
- rag_search: Search the knowledge base of academic papers

When a user asks you to do something that requires a tool, use the appropriate tool. Be helpful and explain what you're doing.

For coding tasks, you can use terminal commands to:
- List files and directories
- Run scripts and commands
- Use git for version control
- Install packages
- And more

For research questions, you can search the knowledge base of academic papers.

Always be careful with terminal commands and explain what you're doing before executing them."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        return agent
    
    async def process_request(self, user_input: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process a user request through the agent.
        
        Args:
            user_input: The user's input
            chat_history: Optional chat history
            
        Returns:
            Dictionary with response information
        """
        try:
            # Convert chat history to LangChain format
            messages = []
            if chat_history:
                for turn in chat_history:
                    if turn.get("user"):
                        messages.append(HumanMessage(content=turn["user"]))
                    if turn.get("assistant"):
                        messages.append(AIMessage(content=turn["assistant"]))
            
            # Run the agent
            result = await self.agent_executor.ainvoke({
                "input": user_input,
                "chat_history": messages
            })
            
            return {
                "success": True,
                "response": result.get("output", ""),
                "tool_calls": []  # LangChain doesn't expose tool calls directly
            }
            
        except Exception as e:
            logger.error(f"Error processing agent request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_tool_execution(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Handle tool execution requests.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input for the tool
            
        Returns:
            Tool execution result
        """
        try:
            # Find the tool
            tool = None
            for t in self.tools:
                if t.name == tool_name:
                    tool = t
                    break
            
            if not tool:
                return f"Tool '{tool_name}' not found"
            
            # Execute the tool
            if tool_name == "terminal_command":
                return tool._run(tool_input.get("command", ""))
            elif tool_name == "rag_search":
                return tool._run(tool_input.get("query", ""), tool_input.get("k", 5))
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return f"Error executing tool: {str(e)}"
    
    async def process_inline_request(self, user_input: str, selected_text: str, document_context: str, 
                                   document_path: str = None, line_number: int = None, 
                                   chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process an inline chat request with document context.
        
        Args:
            user_input: User's input
            selected_text: Selected text from the document
            document_context: Context around the selection
            document_path: Path to the document
            line_number: Line number of the selection
            chat_history: Optional chat history
            
        Returns:
            Dictionary with response information
        """
        try:
            # Build context-aware prompt
            context_prompt = f"""You are helping with code in a document.

Document: {document_path or "Unknown"}
Line: {line_number or "Unknown"}

Selected Text:
{selected_text}

Document Context:
{document_context}

User Question: {user_input}

Please help with the user's question, considering the selected text and document context."""

            # Convert chat history to LangChain format
            messages = []
            if chat_history:
                for turn in chat_history:
                    if turn.get("user"):
                        messages.append(HumanMessage(content=turn["user"]))
                    if turn.get("assistant"):
                        messages.append(AIMessage(content=turn["assistant"]))
            
            # Add the current context
            messages.append(HumanMessage(content=context_prompt))
            
            # Get response from LLM
            response = self.llm.invoke({"messages": messages})
            
            return {
                "success": True,
                "response": response.content,
                "tool_calls": []
            }
            
        except Exception as e:
            logger.error(f"Error processing inline request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """
        Get list of available tools.
        
        Returns:
            List of tool information
        """
        tools_info = []
        for tool in self.tools:
            tools_info.append({
                "name": tool.name,
                "description": tool.description
            })
        return tools_info

# Create global instance
agent_service = AgentService() 