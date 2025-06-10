# Creating an Agent Card

## Requirements
- An agent should have an agent card via what is recently known as 
- The Agent card should be stored in a file with the path called .well-known/agent.json
- The card should properly reflect the agent properties

## Agent Card Example

```json
{
  "name": "{agent_name}",
  "description": "This should be a clear, single sentence description of the agent's role",
  "url": "https://example-agent.com",
  "provider": {
    "name": "Example Provider",
    "url": "https://example-provider.com"
  },
  "version": "1.0.0",
  "documentationUrl": "https://example-agent.com/docs",
  "streaming": true,
  "pushNotifications": false,
  "stateTransitionHistory": true,
  "authentication": {
    "scheme": "Bearer",
    "credentials": [
      {
        "type": "api_key",
        "description": "API key for accessing the agent",
        "required": true
      }
    ]
  },
  "defaultInputModes": [
    "text/plain",
    "application/json"
  ],
  "defaultOutputModes": [
    "text/plain",
    "application/json"
  ],
  "skills": [
    {
      "id": "example_skill_1",
      "name": "Example Skill 1",
      "description": "This is an example skill that demonstrates the skill structure",
      "tags": [
        "example",
        "demo"
      ],
      "examples": [
        {
          "input": "Example input for skill 1",
          "output": "Example output from skill 1",
          "description": "Basic usage example"
        }
      ]
    },
    {
      "id": "example_skill_2",
      "name": "Example Skill 2",
      "description": "This is another example skill with custom input/output modes",
      "tags": [
        "example",
        "custom"
      ],
      "examples": [
        {
          "input": "Example input for skill 2",
          "output": "Example output from skill 2",
          "description": "Custom modes example"
        }
      ],
      "inputModes": [
        "text/plain",
        "audio/mpeg"
      ],
      "outputModes": [
        "text/plain",
        "image/png"
      ]
    }
  ]
}
```

## Important Notes
- Model input and output modes for the agent model id string used in agent.py can be found in the model index at https://openrouter.ai/api/v1/models