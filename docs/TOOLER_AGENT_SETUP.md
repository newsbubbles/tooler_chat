# Tooler Agent Setup Guide

This document explains how to set up and integrate the Tooler agent into the tooler_chat application.

## Overview

The Tooler agent is an advanced AI assistant specialized in building custom API clients based on user requirements. It combines:

- Strong research capabilities using web search and scraping
- Code generation for API clients, with type safety
- Best practices for code organization and async programming
- Test-driven development with example usage

## Prerequisites

1. Clone the `tooler` repository alongside your `tooler_chat` repository
2. Set up environment variables for API keys
3. Copy necessary files from the tooler project

## Setup Steps

### 1. Clone Repositories

Ensure both repositories are cloned side-by-side:

```bash
git clone https://github.com/yourorg/tooler.git
git clone https://github.com/yourorg/tooler_chat.git
cd tooler_chat
```

### 2. Set Environment Variables

Create or update your `.env` file with the necessary API keys:

```
OPENAI_API_KEY=your-openai-api-key
OPENROUTER_API_KEY=your-openrouter-api-key
SERPER_API_KEY=your-serper-api-key
```

### 3. Copy Required Files

Run the provided script to copy project_tools from the tooler repository:

```bash
python scripts/copy_tooler_files.py
```

This will create a `project_tools` directory in your tooler_chat project.

### 4. Switch to the Integrated Agent

Run the application using the branch with the agent integration:

```bash
git checkout tooler-integration
./setup.sh
./run.sh
```

## Configuration Options

The agent can be customized through environment variables:

| Variable | Purpose | Default |
|----------|---------|--------|
| OPENAI_API_KEY | OpenAI API access | Required if not using OpenRouter |
| OPENROUTER_API_KEY | Multi-model access via OpenRouter | Optional, preferred |
| SERPER_API_KEY | Web search capability | Required |

## How It Works

The integration works by:

1. Storing the agent system prompt in `backend/app/agents/tooler.md`
2. Using a configuration wrapper in `backend/app/agents/tooler_agent.py`
3. Creating the agent instance on demand in `backend/app/core/agent_manager.py`
4. Integrating with the chat UI in `backend/app/api/chat.py`

## Troubleshooting

Common issues:

- **Missing MCP Servers**: Ensure the copy_tooler_files.py script ran correctly
- **API Key Errors**: Check your .env file and ensure keys are loaded
- **Agent Not Found**: Verify the agent record exists in the database
- **Import Errors**: Check if dependencies are installed

## Development Notes

- The agent expects a PostgreSQL database with UUID primary keys
- The project uses SQLModel as the ORM with Pydantic models
- For local testing, a simplified in-memory database can be used

## Support

If you encounter issues, please check:

1. Application logs for errors
2. The troubleshooting section of this guide
3. Open an issue if problems persist
