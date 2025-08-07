# Fyodorov LLM Agents

A Python library for building and managing LLM-powered agents with tool integration capabilities.

## Overview

Fyodorov LLM Agents provides a framework for creating AI agents that can:
- Execute custom prompts with various LLM providers
- Integrate with external tools via OpenAPI specifications  
- Manage conversation history and state
- Handle function calling and structured responses
- Support multiple LLM providers through LiteLLM integration

## Key Features

### 🤖 Agent Management
- Create and configure AI agents with custom names, descriptions, and prompts
- Validate agent configurations and enforce size limits
- Support for public and private agent visibility

### 🔧 Tool Integration
- Connect agents to external APIs using OpenAPI specifications
- MCP (Model Context Protocol) tool support
- Structured tool calling with validation
- Tool discovery and management

### 🧠 LLM Support
- Multiple provider support via LiteLLM (OpenAI, Anthropic, etc.)
- Configurable model parameters and API endpoints
- Function calling capabilities with structured responses

### 💬 Instance Management
- Conversation history tracking
- Session state management
- Chat context preservation

## Installation

```bash
pip install fyodorov-llm-agents
```

## Dependencies

- `requests` - HTTP client for API calls
- `pydantic` - Data validation and serialization
- `openai` - OpenAI API client
- `pyyaml` - YAML parsing
- `litellm` - Multi-provider LLM integration

## Quick Start

```python
from fyodorov_llm_agents.agents.agent_model import Agent
from fyodorov_llm_agents.models.llm_model import LLMModel

# Create an agent
agent = Agent(
    name="My Assistant",
    description="A helpful AI assistant",
    prompt="You are a helpful assistant that can answer questions.",
    tools=["calculator", "weather"],
    model=LLMModel(name="gpt-4")
)

# Validate the agent
agent.validate()
```

## Architecture

The library is organized into several key components:

- **`agents/`** - Core agent models and services
- **`tools/`** - Tool integration and MCP support  
- **`models/`** - LLM model definitions and services
- **`providers/`** - LLM provider configurations
- **`instances/`** - Conversation instance management

For detailed architecture documentation, see [Architecture.md](Architecture.md).

## Contributing

This project is part of the Fyodorov AI suite. For issues and contributions, please visit the [GitHub repository](https://github.com/FyodorovAI/fyodorov-llm-agents).

## License

MIT License - see the project repository for details.