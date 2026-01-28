"""
OpenRouter API Service
Handles communication with OpenRouter for AI model inference
"""
import requests
import json
import re
from typing import Optional, Dict, Any, List
from ..config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_CLASSIFIER_MODEL,
    OPENROUTER_RESPONSE_MODEL
)


def test_openrouter_connection() -> bool:
    """Test if the OpenRouter API is reachable"""
    try:
        if not OPENROUTER_API_KEY:
            print("❌ OpenRouter API key not configured")
            return False
            
        print(f"Testing connection to OpenRouter...")
        response = requests.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ OpenRouter connection successful")
            return True
        else:
            print(f"❌ OpenRouter connection failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing OpenRouter connection: {e}")
        return False


def call_openrouter(
    prompt: str,
    model: str = None,
    system_prompt: str = None,
    json_mode: bool = False,
    max_tokens: int = 1024
) -> Optional[str]:
    """
    Make a request to OpenRouter API
    
    Args:
        prompt: The user prompt
        model: Model to use (defaults to response model)
        system_prompt: Optional system prompt
        json_mode: Whether to request JSON output
        max_tokens: Maximum tokens in response
        
    Returns:
        The model's response text or None on error
    """
    if not OPENROUTER_API_KEY:
        print("❌ OpenRouter API key not configured")
        return None
        
    model = model or OPENROUTER_RESPONSE_MODEL
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/email-support-system",
        "X-Title": "Email Support System"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    
    # Add response format for JSON mode
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    
    try:
        print(f"Calling OpenRouter with model: {model}")
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ OpenRouter API error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return content
        
    except Exception as e:
        print(f"❌ Error calling OpenRouter: {e}")
        return None


def call_openrouter_structured(
    prompt: str,
    model: str = None,
    system_prompt: str = None,
    max_tokens: int = 1024
) -> Optional[Dict[str, Any]]:
    """
    Make a request to OpenRouter API and parse JSON response
    
    Returns:
        Parsed JSON dict or None on error
    """
    model = model or OPENROUTER_CLASSIFIER_MODEL
    
    response = call_openrouter(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        json_mode=True,
        max_tokens=max_tokens
    )
    
    if not response:
        return None
        
    try:
        # Try to parse JSON from response
        # Sometimes models wrap JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            response = json_match.group(1)
        
        # Clean up common issues
        response = response.strip()
        
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Raw response: {response[:500]}")
        return None


def generate_ai_response(
    customer_query: str,
    context: str = "",
    draft_response: str = ""
) -> str:
    """
    Generate an AI response for a customer query
    
    Args:
        customer_query: The customer's email content
        context: RAG context from knowledge base
        draft_response: Optional draft to improve
        
    Returns:
        The AI-generated response
    """
    system_prompt = """You are a professional customer support agent for StudyFate. 
Your task is to provide helpful, empathetic, and accurate responses to customer inquiries.

Guidelines:
- Be professional yet friendly
- Address the customer's concerns directly
- If you have context from the knowledge base, use it accurately
- Keep responses concise but complete
- DO NOT include greetings like "Dear Customer" or signatures - these are added automatically
- DO NOT include any meta-commentary or thinking sections"""

    # Build the prompt
    prompt_parts = []
    
    if context:
        prompt_parts.append(f"**Knowledge Base Context:**\n{context}\n")
    
    prompt_parts.append(f"**Customer Query:**\n{customer_query}\n")
    
    if draft_response:
        prompt_parts.append(f"**Draft Response to Improve:**\n{draft_response}\n")
        prompt_parts.append("Please improve this draft response using the context provided.")
    else:
        prompt_parts.append("Please provide a helpful response to this customer query.")
    
    prompt = "\n".join(prompt_parts)
    
    response = call_openrouter(
        prompt=prompt,
        model=OPENROUTER_RESPONSE_MODEL,
        system_prompt=system_prompt,
        max_tokens=1024
    )
    
    if response:
        # Clean up the response
        response = clean_ai_response(response)
        return response
    else:
        return "I apologize, but I'm unable to generate a response at this time. A support agent will assist you shortly."


def clean_ai_response(response: str) -> str:
    """Clean up the AI response"""
    # Remove any thinking sections
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Remove common prefixes
    prefixes_to_remove = [
        "Here's an improved response:",
        "Here is the improved response:",
        "Here's my response:",
        "Response:",
        "---",
        "```"
    ]
    
    for prefix in prefixes_to_remove:
        if response.strip().startswith(prefix):
            response = response.replace(prefix, "", 1).strip()
    
    # Remove trailing markers
    response = response.replace("---", "").replace("```", "")
    
    # Remove greetings/signatures if AI added them anyway
    response = re.sub(r'^Dear Customer,?\s*', '', response, flags=re.IGNORECASE)
    response = re.sub(r'^Hello\s+\w+,?\s*', '', response, flags=re.IGNORECASE)  # Remove "Hello Name,"
    response = re.sub(r'^Hi\s+\w+,?\s*', '', response, flags=re.IGNORECASE)     # Remove "Hi Name,"
    response = re.sub(r'^Dear\s+\w+,?\s*', '', response, flags=re.IGNORECASE)   # Remove "Dear Name,"
    response = re.sub(r'^Hey\s+\w+,?\s*', '', response, flags=re.IGNORECASE)    # Remove "Hey Name,"
    response = re.sub(r'Thanks,?\s*The StudyFate Team\s*$', '', response, flags=re.IGNORECASE)
    response = re.sub(r'Best regards,?\s*.*$', '', response, flags=re.IGNORECASE | re.MULTILINE)
    response = re.sub(r'Sincerely,?\s*.*$', '', response, flags=re.IGNORECASE | re.MULTILINE)
    
    return response.strip()
