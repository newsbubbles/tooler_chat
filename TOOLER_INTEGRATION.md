# Tooler Agent Integration

This branch contains the integration of the Tooler agent from the `tooler` project into the `tooler_chat` application.

## What's Included

### Agent Infrastructure
- **Agent Prompt**: Copied the agent prompt from the tooler project
- **Agent Manager**: Created a utility to manage agent instances and caching
- **Agent Configuration**: Set up the tooler agent with proper MCP servers

### Backend Integration
- **Chat API Updates**: Modified chat endpoints to use the new agent system
- **Database Support**: Added migration script for the default agent
- **System Initialization**: Enhanced startup to ensure the tooler agent exists

### Utilities and Documentation
- **File Copy Script**: Added script to copy necessary files from tooler
- **Integration Script**: Created apply_tooler_integration.sh for easy deployment
- **Setup Documentation**: Added detailed guide on setting up the tooler agent

## How to Apply

1. Ensure you have both `tooler` and `tooler_chat` repositories checked out
2. Make sure they're in adjacent directories (or update the paths in the scripts)
3. Run the integration script:

```bash
chmod +x apply_tooler_integration.sh
./apply_tooler_integration.sh
```

## Required Environment Variables

- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` for the language model
- `SERPER_API_KEY` for web search capabilities

## Technical Details

### Agent Architecture
- Uses the PydanticAI Agent with MCP base system
- Connects to the project_tools MCP servers for file and search operations
- Uses Claude 3.7 Sonnet through OpenRouter as the default model

### Integration Strategy
- Created a clean abstraction layer for agent management
- Made minimal changes to existing code
- Added error handling and logging throughout
- Ensured proper cleanup on application shutdown

### Future Improvements
- Add more agents with different capabilities
- Enhance the agent manager with more features
- Add UI support for agent configuration
- Improve database migrations for easier deployment

## Testing

After applying the integration:

1. Start the application with `./run.sh`
2. Log in to the web interface
3. Create a new chat session
4. You should see the Tooler agent available
5. Test sending a message to generate a client for an API

## Troubleshooting

See `docs/TOOLER_AGENT_SETUP.md` for detailed troubleshooting tips.

## Credits

This integration is based on the original `tooler` project.
