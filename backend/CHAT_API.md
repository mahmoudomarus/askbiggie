# Simple Chat API Documentation

The Simple Chat API provides direct LLM communication without the complex agent system, tools, or sandboxes. Perfect for API integrations, simple conversational AI, and quick prototyping.

## Base URL
```
https://askbiggie-a4fdf63d7e8b.herokuapp.com/api/chat
```

## Authentication
All endpoints require JWT authentication via Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### 1. Simple Chat - `/chat/simple` (POST)

Full-featured chat endpoint with support for conversation history, custom system prompts, and streaming.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello, how are you?"},
    {"role": "assistant", "content": "I'm doing well, thank you!"},
    {"role": "user", "content": "What's the weather like?"}
  ],
  "model": "gpt-4o",  // Optional, defaults to system default
  "temperature": 0.1,  // Optional, defaults to 0.1
  "max_tokens": 1000,  // Optional
  "stream": true,      // Optional, defaults to true
  "system_prompt": "You are a helpful assistant."  // Optional
}
```

**Streaming Response** (when `stream: true`):
```
data: {"content": "Hello", "type": "content"}
data: {"content": "!", "type": "content"}
data: {"type": "complete", "message": {"role": "assistant", "content": "Hello!"}, "model": "gpt-4o"}
```

**Non-streaming Response** (when `stream: false`):
```json
{
  "message": {
    "role": "assistant",
    "content": "I'm an AI assistant. I don't experience weather, but I can help you find weather information if you provide a location!"
  },
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 25,
    "total_tokens": 40
  }
}
```

### 2. Quick Chat - `/chat/quick` (POST)

Ultra-simple endpoint for quick questions. Just send a prompt and get a response.

**Request Body:**
```json
{
  "prompt": "What is the capital of France?",
  "model": "gpt-4o"  // Optional
}
```

**Response:**
```json
{
  "message": {
    "role": "assistant", 
    "content": "The capital of France is Paris."
  },
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 7,
    "total_tokens": 15
  }
}
```

### 3. Available Models - `/chat/models` (GET)

Get list of models available to the current user.

**Response:**
```json
{
  "models": [
    "gpt-4o",
    "gpt-4o-mini", 
    "claude-3-5-sonnet-20241022",
    "gemini-1.5-pro-latest"
  ],
  "default_model": "gpt-4o"
}
```

## Usage Examples

### JavaScript/TypeScript Example
```javascript
const response = await fetch('/api/chat/simple', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`
  },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: 'Explain quantum computing in simple terms' }
    ],
    model: 'gpt-4o',
    stream: false
  })
});

const data = await response.json();
console.log(data.message.content);
```

### Python Example
```python
import requests

response = requests.post(
    'https://askbiggie-a4fdf63d7e8b.herokuapp.com/api/chat/simple',
    headers={
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    },
    json={
        'messages': [
            {'role': 'user', 'content': 'What is machine learning?'}
        ],
        'model': 'gpt-4o',
        'stream': False
    }
)

data = response.json()
print(data['message']['content'])
```

### cURL Example
```bash
curl -X POST \
  https://askbiggie-a4fdf63d7e8b.herokuapp.com/api/chat/quick \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a haiku about coding",
    "model": "gpt-4o"
  }'
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 402 Payment Required
```json
{
  "error": "Billing limit reached",
  "message": "You have reached your monthly usage limit",
  "subscription": {...}
}
```

### 403 Forbidden
```json
{
  "error": "Model access denied", 
  "message": "You don't have access to this model",
  "allowed_models": ["gpt-4o-mini", "claude-3-haiku"]
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

## Key Differences from Agent API

| Feature | Simple Chat API | Agent API |
|---------|----------------|-----------|
| **Complexity** | Direct LLM communication | Multi-layered agent system |
| **Tools** | None | 20+ tools (web search, file ops, etc.) |
| **Sandboxes** | None | Full Linux environment |
| **Workflows** | None | Complex multi-step automation |
| **File Uploads** | Not supported | Full file processing |
| **Use Cases** | Chat, Q&A, API integration | Complex tasks, automation |
| **Response Speed** | Fast (direct) | Slower (tool processing) |
| **Resource Usage** | Minimal | Higher (sandbox, tools) |

## Frontend Integration

In the frontend, users can now choose "Simple Chat" from the agent selector, which provides:
- Direct AI conversation without tools
- Perfect for quick questions and research
- No complex features or workflows
- Faster response times
- Ideal for users who want straightforward AI assistance

The agent selector now clearly distinguishes between:
- **Simple Chat** - Direct LLM communication
- **Custom Agents** - User-created agents with tools/workflows
- **Predefined Agents** - Pre-configured specialized agents

## Best Practices

1. **Use Simple Chat for:**
   - Quick questions and answers
   - Research and information gathering
   - Creative writing assistance
   - Basic problem solving
   - API integrations with other UIs

2. **Use Agent API for:**
   - Complex multi-step tasks
   - File processing and analysis
   - Web scraping and research
   - Code execution and development
   - Workflow automation

3. **Model Selection:**
   - Check available models first via `/chat/models`
   - Use appropriate models for your use case
   - Consider cost vs. capability trade-offs

4. **Streaming:**
   - Use streaming for better user experience
   - Non-streaming for programmatic integration
   - Handle streaming responses properly

This Simple Chat API provides the perfect balance of simplicity and power for direct AI communication! 