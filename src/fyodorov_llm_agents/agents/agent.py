import os
import re
import requests
import queue
import threading
import json
import yaml
from pydantic import BaseModel
from openai import OpenAI as oai
from litellm import completion
from fyodorov_llm_agents.tools.tool import Tool

MAX_NAME_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 280
VALID_CHARACTERS_REGEX = r'^[a-zA-Z0-9\s.,!?:;\'"-]+$'

class Agent(BaseModel):
    api_key: str = None
    tools: [Tool] = []
    rag: [] = []
    model: str | None = None
    modelid: str | None = None
    name: str = "My Agent"
    description: str = "My Agent Description"
    prompt: str = "My Prompt"
    prompt_size: int = 10000

    class Config:
        arbitrary_types_allowed = True

    def validate(self):
        Agent.validate_name(self.name)
        Agent.validate_description(self.description)
        Agent.validate_prompt(self.prompt, self.prompt_size)

    @staticmethod
    def validate_name(name: str) -> str:
        if not name:
            raise ValueError('Name is required')
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError('Name exceeds maximum length')
        if not re.match(VALID_CHARACTERS_REGEX, name):
            raise ValueError('Name contains invalid characters')
        return name

    @staticmethod
    def validate_description(description: str) -> str:
        if not description:
            raise ValueError('Description is required')
        if len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValueError('Description exceeds maximum length')
        if not re.match(VALID_CHARACTERS_REGEX, description):
            raise ValueError('Description contains invalid characters')
        return description

    @staticmethod
    def validate_prompt(prompt: str, prompt_size: int) -> str:
        if not prompt:
            raise ValueError('Prompt is required')
        if len(prompt) > prompt_size:
            raise ValueError('Prompt exceeds maximum length')
        return prompt

    def to_dict(self) -> dict:
        return {
            'model': self.model,
            'name': self.name,
            'description': self.description,
            'prompt': self.prompt,
            'prompt_size': self.prompt_size,
            'tools': self.tools,
            'rag': self.rag,
        }

    def call_with_fn_calling(self, prompt: str = "", input: str = ""):
        # Set environmental variable
        os.environ["OPENAI_API_KEY"] = self.api_key
        messages: [] = [
            {"content": prompt, "role": "system"},
            { "content": input, "role": "user"},
        ]
        tools = [tool.get_function() for tool in self.tools]
        if tools:
            print(f"calling litellm with model {self.model}, messages: {messages}, max_retries: 0, tools: {tools}")
            response = completion(model=self.model, messages=messages, max_retries=0, tools=tools, tool_choice="auto")
        else:
            print(f"calling litellm with model {self.model}, messages: {messages}, max_retries: 0")
            response = completion(model=self.model, messages=messages, max_retries=0)
        print(f"Response: {response}")
        answer = response.choices[0].message.content
        print(f"Answer: {answer}")
        return {
            "answer": answer
        }

    @staticmethod
    def from_yaml(yaml_str: str):
        """Instantiate Agent from YAML."""
        if not yaml_str:
            raise ValueError('YAML string is required')
        agent_dict = yaml.safe_load(yaml_str)
        agent = Agent(**agent_dict)
        agent.validate()
        return agent

    @staticmethod
    def from_dict(agent_dict: dict):
        """Instantiate Agent from dict."""
        if not agent_dict:
            raise ValueError('Agent dict is required')
        agent = Agent(**agent_dict)
        agent.validate()
        return agent
