from datetime import datetime, timezone
import os
import logging

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables for API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def load_agent_prompt(agent_path: str) -> str:
    """Loads agent prompt file and replaces time_now var with current time"""
    logger.info(f"Loading agent prompt from {agent_path}")
    time_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(agent_path, "r") as f:
            agent_prompt = f.read()
        return agent_prompt.replace('{time_now}', time_now)
    except Exception as e:
        logger.error(f"Failed to load agent prompt: {str(e)}")
        # Return a minimal prompt if the file can't be loaded
        return "You are a helpful assistant. Today is {time_now}.".replace('{time_now}', time_now)


def create_tooler_agent(project_tools_path: str = "project_tools", 
                      agent_prompt_path: str = "app/agents/tooler.md") -> Agent:
    """Create the Tooler agent with proper configuration
    
    Args:
        project_tools_path: Path to the project_tools directory with MCP servers
        agent_prompt_path: Path to the agent prompt markdown file
    
    Returns:
        Configured Agent instance
    """
    # Set up model using OpenRouter or fallback to OpenAI
    if OPENROUTER_API_KEY:
        provider = OpenAIProvider(
            base_url='https://openrouter.ai/api/v1',
            api_key=OPENROUTER_API_KEY
        )
        logger.info("Using OpenRouter as provider")
    else:
        provider = OpenAIProvider(api_key=OPENAI_API_KEY)
        logger.info("Using OpenAI as provider")
    
    # Default to Claude 3.7 Sonnet as our target model
    model = OpenAIModel(
        'anthropic/claude-3.7-sonnet',
        provider=provider
    )
    
    # Setup environment variables for MCP servers
    env = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "SERPER_API_KEY": SERPER_API_KEY,
        "ROOT_FOLDER": "./data/projects"
    }
    
    # Setup MCP Servers
    mcp_servers = [
        # Project Tools MCP for working with files, variables, etc.
        MCPServerStdio('python', [f'{project_tools_path}/project_tools.py'], env=env),
        # Search and Scraping MCP for web searching and scraping
        MCPServerStdio('python', [f"{project_tools_path}/serper_scrape_mcp.py"], env=env),
    ]
    
    # Load the agent prompt
    agent_prompt = load_agent_prompt(agent_prompt_path)
    
    # Create and return the agent
    return Agent(model, mcp_servers=mcp_servers, system_prompt=agent_prompt)
