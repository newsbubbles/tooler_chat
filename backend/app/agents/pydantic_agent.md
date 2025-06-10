## Creating an Agent
An agent is an important part of end-to-end testing of the full agentic stack the MCP Server will be used in.
It is important to remember that even though MCP server is called a server, the client is actually instantiating the server through stdio, and that client is the Agent.

### Setup
An agent consists of two parts:
- An agentic system prompt, written in markdown and stored in {project_path}/agents/{agent_name}.md
- An agent.py file which holds the PydanticAI Agent that loads the mcp server inside it placed in the root project folder.

Optional
- Make a prompts.json file which holds a set of test prompts that could be sent to the agent for end-to-end testing.

## System Prompt Instructions
- The system prompt for the agent should define the operational constraints of the agent
- It should include some basic sections for Identity, and then instruction blocks for how to reply or behave given context
- Avoid describing tools (those are auto-discovered by the agent), instead perhaps make sections about benefits, possible workflows
- Keep the overall length of instructions short, as more instructions will be added during testing
- The instructions should be model/LLM agnostic

## Agentic Script
The following is an example of a PydanticAI Agent. Follow this flow, and make sure to account for the required environment variables.

```python
# PydanticAI Agent with MCP

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.agent import AgentRunResult

from dotenv import load_dotenv
import os

load_dotenv()

import logfire
logfire.configure(token=os.getenv("LOGFIRE_API_KEY"))
logfire.instrument_openai()

# Set up OpenRouter based model
API_KEY = os.getenv('OPENROUTER_API_KEY')
model = OpenAIModel(
    'anthropic/claude-3.7-sonnet',
    provider=OpenAIProvider(
        base_url='https://openrouter.ai/api/v1', 
        api_key=API_KEY
    ),
)

# MCP Environment variables
env = {
    "SOME_API_KEY": os.getenv("SOME_API_KEY"),
    "ANOTHER_API_KEY": os.getenv("ANOTHER_API_KEY"),
}

mcp_servers = [
    MCPServerStdio('python', ['{project_path}/mcp_server.py'], env=env),
]

from datetime import datetime, timezone

# Set up Agent with Server
agent_name = "{agent_name}"
def load_agent_prompt(agent:str):
    """Loads given agent replacing `time_now` var with current time"""
    print(f"Loading {agent}")
    time_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open("{project_path}/agents/" + f"{agent}.md", "r") as f:
        agent_prompt = f.read()
    agent_prompt = agent_prompt.replace('{time_now}', time_now)
    return agent_prompt

# Load up the agent system prompt
agent_prompt = load_agent_prompt(agent_name)
print(agent_prompt)
agent = Agent(model, mcp_servers=mcp_servers, system_prompt=agent_prompt)

import random, traceback

async def main():
    """CLI testing in a conversation with the agent"""
    async with agent.run_mcp_servers(): 

        result:AgentRunResult = None

        while True:
            if result:
                print(f"\n{result.output}")
            user_input = input("\n> ")
            err = None
            for i in range(0, 3):
                try:
                    result = await agent.run(
                        user_input, 
                        message_history=None if result is None else result.all_messages()
                    )
                    break
                except Exception as e:
                    err = e
                    traceback.print_exc()
                    await asyncio.sleep(2)
            if result is None:
                print(f"\nError {err}. Try again...\n")
                continue

        
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Optional Agent Script Updates
- Use argparse to allow user to select model string for the OpenAIModel config, keeping the default as hardcoded above

### Memory Update Note
- Current version of Claude Sonnet is 3.7