# Debug Instructions for Chat Streaming Issue

## Steps to diagnose and fix the issue:

### 1. Add Enhanced Logging & Debugging to chat.py

Replace the existing stream_chat_message function in backend/app/api/chat.py with the enhanced version from debug_chat_endpoint.py. This will give us detailed step-by-step logs of what's happening.

### 2. Enable MAX_DEBUG Mode

Edit your .env file to enable maximum debugging:

```
LOG_LEVEL=DEBUG
STRUCTURED_LOGS=true
MAX_DEBUG=true
```

Restart the backend service to apply these changes.

### 3. Reproduce the Issue

1. Open the Tooler Chat UI
2. Start a new chat with the Tooler agent
3. Send a first message and observe that it doesn't respond
4. Send a second message and observe the "cached" response

### 4. Check the Logs

Open multiple terminal windows to watch different log files:

```bash
# Terminal 1: Watch chat logs
docker-compose exec backend tail -f /app/logs/chat.log

# Terminal 2: Watch error logs
docker-compose exec backend tail -f /app/logs/error.log

# Terminal 3: Watch tool calls
docker-compose exec backend tail -f /app/logs/tool_calls.log
```

### 5. Check These Specific Issues

#### a. Response Handling

Look for these issues in the logs:
- Is the first message being processed but failing to send responses to the frontend?
- Is there a bug in updating the model message with the complete response?
- Are there streaming issues with the first message?

#### b. Message Storage

- Is the first message properly saved to the database?
- Is the agent response to the first message saved but not displayed?

#### c. Agent Initialization

- Is there a delay in initializing the agent for the first message?
- Are the MCP servers starting correctly?

#### d. Frontend Issues

- Is the frontend correctly receiving and displaying streaming updates?
- Are there JavaScript errors in the browser console?

### 6. Likely Fixes

Based on the findings, these are the likely fixes:

1. **If responses are generated but not displayed**: Check the frontend's handling of streaming responses

2. **If agent cache is the issue**: Clean the cache between messages:
```python
# In backend/app/core/agent_manager.py
def clear_agent_cache(agent_id):
    # Clear any cached data for this agent
    if agent_id in _agent_cache:
        del _agent_cache[agent_id]
```

3. **If message history management is the issue**: Fix message history retrieval

4. **If streaming implementation is the issue**: Ensure complete_response is reset between messages

### 7. Advanced Troubleshooting

If the issue persists, you might need to:

1. Debug agent initialization with a test script
2. Verify the streaming implementation by creating a simple test endpoint
3. Check for resource limitations (memory, CPU) affecting the agent performance
