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

### How to Get JWT Tokens

#### Method 1: Use the Frontend (Recommended)
The easiest way to get a JWT token is through the main application:

1. **Sign up/Login** at https://askbiggie.bignoodle.com/auth
2. **Open Developer Tools** (F12) in your browser
3. **Go to Console** and run:
   ```javascript
   // Get the current session and token
   const { data: { session } } = await window.supabase.auth.getSession();
   console.log('Your JWT Token:', session.access_token);
   ```
4. **Copy the token** and use it in your API calls

#### Method 2: Programmatic Login (For Applications)

```javascript
// Using Supabase client in your application
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'YOUR_SUPABASE_URL', 
  'YOUR_SUPABASE_ANON_KEY'
)

// Login with email/password
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'your-email@example.com',
  password: 'your-password'
})

if (data.session) {
  const jwtToken = data.session.access_token;
  console.log('JWT Token:', jwtToken);
  
  // Use this token in your API calls
  const response = await fetch('/api/chat/simple', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwtToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: 'Hello!' }]
    })
  });
}
```

#### Method 3: Environment Variables (For Server-Side)

```bash
# Create a long-lived service account or use your personal token
ASKBIGGIE_JWT_TOKEN=your_jwt_token_here
```

```python
import os
import requests

token = os.getenv('ASKBIGGIE_JWT_TOKEN')
response = requests.post(
    'https://askbiggie-a4fdf63d7e8b.herokuapp.com/api/chat/simple',
    headers={'Authorization': f'Bearer {token}'},
    json={'messages': [{'role': 'user', 'content': 'Hello!'}]}
)
```

### Authentication Endpoints

**Sign Up:**
- **Frontend:** https://askbiggie.bignoodle.com/auth?mode=signup
- **Programmatic:** Use Supabase client `signUp()` method

**Sign In:**
- **Frontend:** https://askbiggie.bignoodle.com/auth
- **Programmatic:** Use Supabase client `signInWithPassword()` method

**OAuth Options:**
- Google OAuth (via frontend)
- GitHub OAuth (via frontend)

### Token Management

**Token Expiration:**
- JWT tokens expire after 1 hour (3600 seconds)
- You'll receive a 401 Unauthorized response when tokens expire
- Refresh tokens automatically when using Supabase client
- For manual API calls, you'll need to re-authenticate

**For Supabase Configuration:**
```javascript
// These are the public configuration values
const supabaseUrl = 'https://your-supabase-url'  // Available in frontend env
const supabaseAnonKey = 'your-anon-key'          // Available in frontend env

// Initialize Supabase client
const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

**Quick Test:**
```bash
# Test your token (replace YOUR_TOKEN with actual token)
curl -X GET \
  https://askbiggie-a4fdf63d7e8b.herokuapp.com/api/chat/models \
  -H "Authorization: Bearer YOUR_TOKEN"
```

If you get a successful response with available models, your token is working!

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

## Step-by-Step Getting Started

### Quick Start (5 minutes)

1. **Get Your Token:**
   ```javascript
   // Go to https://askbiggie.bignoodle.com/auth, login, then run in console:
   const { data: { session } } = await window.supabase.auth.getSession();
   console.log('Token:', session.access_token);
   ```

2. **Test the API:**
   ```bash
   curl -X POST \
     https://askbiggie-a4fdf63d7e8b.herokuapp.com/api/chat/quick \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, test message!"}'
   ```

3. **Start Building:**
   ```javascript
   const response = await fetch('/api/chat/simple', {
     method: 'POST',
     headers: {
       'Authorization': 'Bearer YOUR_TOKEN_HERE',
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       messages: [
         { role: 'user', content: 'What is quantum computing?' }
       ],
       stream: false
     })
   });
   
   const data = await response.json();
   console.log(data.message.content);
   ```

### Ready to Scale?

- Use the `/chat/simple` endpoint for full conversation history
- Enable streaming for better user experience  
- Integrate with your existing authentication system
- Monitor usage via the main dashboard

This Simple Chat API provides the perfect balance of simplicity and power for direct AI communication! 