import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for searching course information.

Tool Usage:
- **search_course_content**: Use for questions about specific course content or detailed educational materials
- **get_course_outline**: Use for questions about course structure, syllabus, or what lessons a course contains (e.g. "what lessons are in X?", "give me an outline of X", "what does X cover?")
- **You may make up to 2 sequential tool calls if the first result is insufficient to fully answer the question**
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Use the appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results"

Outline responses must include:
- Course title and course link
- Each lesson number and lesson title, in order

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._run_tool_loop(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text

    def _run_tool_loop(self, initial_response, api_params: Dict[str, Any], tool_manager) -> str:
        messages = api_params["messages"].copy()
        current_response = initial_response
        last_text = None
        error_occurred = False

        for _ in range(2):
            messages.append({"role": "assistant", "content": current_response.content})

            tool_results = []
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Tool execution failed: {str(e)}",
                        })
                        error_occurred = True
                        break

            messages.append({"role": "user", "content": tool_results})

            if error_occurred:
                break

            # tools must be included so the API accepts message history with tool_use blocks
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": api_params["system"],
                "tools": api_params["tools"],
                "tool_choice": api_params["tool_choice"],
            }
            current_response = self.client.messages.create(**next_params)

            if current_response.stop_reason != "tool_use":
                return current_response.content[0].text

            for block in current_response.content:
                if block.type == "text":
                    last_text = block.text
                    break

        return last_text or "Unable to generate a response."