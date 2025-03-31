import ollama
import requests
import re
from typing import Optional
from ..config.settings import OLLAMA_HOST, OLLAMA_MODEL

def test_ollama_connection() -> bool:
    """Test if the Ollama server is reachable and the model is available"""
    try:
        print(f"Testing connection to Ollama server at {OLLAMA_HOST}...")
        # Try a basic request to get model list
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code != 200:
            print(f"Error connecting to Ollama: HTTP status {response.status_code}")
            return False
            
        models = response.json().get('models', [])
        print(f"Found {len(models)} models on Ollama server")
        
        # Check if our model is available
        model_names = [m.get('name') for m in models]
        if OLLAMA_MODEL not in model_names:
            print(f"Warning: Model '{OLLAMA_MODEL}' not found in available models: {model_names}")
            return False
            
        print(f"Ollama connection test successful - model '{OLLAMA_MODEL}' is available")
        return True
    except Exception as e:
        print(f"Error testing Ollama connection: {e}")
        print(f"Make sure Ollama is running at {OLLAMA_HOST}")
        return False

def process_with_deepseek(original_query: str, response_text: str) -> str:
    """Process a response with DeepSeek via Ollama"""
    print(f"Processing response with Ollama model {OLLAMA_MODEL} via {OLLAMA_HOST}...")
    
    # Shorten the original query if it's too long
    max_len = 1000
    if len(original_query) > max_len:
        original_query = original_query[:max_len] + "..."
    
    prompt = f"""
    You are a professional customer support agent from StudyFate. Provide a direct, concise, and helpful response.
    
    Original customer query:
    {original_query}
    
    Support agent's response:
    {response_text}
    
    Your task:
    1. Improve the response to be more helpful, professional, and empathetic.
    2. Maintain the key information from the original response.
    3. Ensure the tone is consistent with our brand and the response is clear and concise.
    4. Format any bullet points with proper line breaks.
    5. Provide ONLY the improved response text without any explanations, thoughts, or formatting markers.
    6. DO NOT include any greeting or signature - these will be added automatically.
    7. DO NOT include any <think> sections, meta-commentary, or notes to yourself.
    """
    
    try:
        print(f"Sending request to Ollama at {OLLAMA_HOST} using model {OLLAMA_MODEL}...")
        
        # Check if OLLAMA_MODEL contains a slash - if so, it might not work with ollama.chat
        if '/' in OLLAMA_MODEL:
            # Use direct API call via requests instead
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            if response.status_code != 200:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")
                
            result = response.json()
            improved_response = result.get('response', '')
        else:
            # Use ollama library
            response = ollama.chat(model=OLLAMA_MODEL, messages=[
                {"role": "user", "content": prompt}
            ])
            improved_response = response['message']['content']
        
        # Clean up the response
        improved_response = clean_ollama_response(improved_response)
        
        # Add greeting and signature
        formatted_response = f"Dear Customer,\n\n{improved_response}\n\nThanks,\nThe StudyFate Team"
            
        return formatted_response
    except Exception as e:
        print(f"Error processing with Ollama: {e}")
        print("Returning original response without AI processing")
        # If Ollama fails, return the original response with proper greeting and signature
        original_with_format = f"Dear Customer,\n\n{response_text}\n\nThanks,\nThe StudyFate Team"
        return original_with_format

def clean_ollama_response(response: str) -> str:
    """Clean up the response from Ollama"""
    # Remove any thinking sections
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Remove common prefixes that models like to add
    prefixes_to_remove = [
        "Here's an improved response:",
        "Here is the improved response:",
        "Improved response:",
        "I would respond with:",
        "I would say:",
        "Response:",
        "---",
        "```"
    ]
    
    for prefix in prefixes_to_remove:
        if response.strip().startswith(prefix):
            response = response.replace(prefix, "", 1).strip()
    
    # Remove any trailing formatting markers
    response = response.replace("---", "").replace("```", "")
    
    # Remove Dear Customer or Thanks from AI output if it added them anyway
    response = re.sub(r'^Dear Customer,?\s*', '', response, flags=re.IGNORECASE)
    response = re.sub(r'Thanks,?\s*The StudyFate Team\s*$', '', response, flags=re.IGNORECASE)
    
    return response.strip() 