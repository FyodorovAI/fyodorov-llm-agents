import os
import re
import requests
import queue
import threading
import json
import yaml
from pydantic import BaseModel, HttpUrl
from openai import OpenAI as oai
import litellm
from fyodorov_llm_agents.tools.tool import Tool

MAX_NAME_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 280
VALID_CHARACTERS_REGEX = r'^[a-zA-Z0-9\s.,!?:;\'"-_]+$'

class Agent(BaseModel):
    api_key: str | None = None
    api_url: HttpUrl | None = None
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

    def call_with_fn_calling(self, input: str = "", history = []) -> dict:
        litellm.set_verbose = True
        model = self.model
        # Set environmental variable
        if self.api_key.startswith('sk-'):
            os.environ["OPENAI_API_KEY"] = self.api_key
            self.api_url = "https://api.openai.com/v1"
        elif self.api_key and self.api_key != '':
            model = 'mistral/'+self.model
            os.environ["MISTRAL_API_KEY"] = self.api_key
            self.api_url = "https://api.mistral.ai/v1"
        else:
            print("Provider Ollama")
            model = 'ollama/'+self.model
            if self.api_url is None:
                self.api_url = "https://api.ollama.ai/v1"

        base_url = str(self.api_url)
        if base_url and base_url[-1] == '/':
            print("Removing trailing slash")
            base_url = base_url[:-1]

        messages: [] = [
            {"content": self.prompt, "role": "system"},
            *history,
            { "content": input, "role": "user"},
        ]
        print(f"Tools: {self.tools}")
        tools = [tool.get_function() for tool in self.tools]
        if tools and litellm.supports_function_calling(model=model):
            print(f"calling litellm with model {model}, tools: {tools}, messages: {messages}, max_retries: 0, history: {history}, base_url: {base_url}")
            response = litellm.completion(model=model, messages=messages, max_retries=0, tools=tools, tool_choice="auto", base_url=base_url)
        else:
            print(f"calling litellm with model {model}, messages: {messages}, max_retries: 0, history: {history}, base_url: {base_url}")
            response = litellm.completion(model=model, messages=messages, max_retries=0, base_url=base_url)
        print(f"Response: {response}")
        tool_calls = []
        if hasattr(response, 'tool_calls'):
            tool_calls = response.tool_calls if response.tool_calls else []
        if tool_calls:
            for tool_call in tool_calls:
                print(f"Calling function {tool_call.function.name}")
                function_args = json.loads(tool_call.function.arguments)
                function_response = self.call_api(
                    url=function_args["url"],
                    method=function_args["method"],
                    body=function_args["body"],
                )
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )  # extend conversation with function response
            response = litellm.completion(
                model=model,
                messages=messages,
            )  # get a new response from the model where it can see the function response
            print("\nSecond LLM response:\n", response)
        answer = response.choices[0].message.content
        print(f"Answer: {answer}")
        return {
            "answer": answer,

        }

    @staticmethod
    def call_api(url: str = "", method: str = "GET", body: dict = {}) -> dict:
        if not url:
            raise ValueError('API URL is required')
        try:
            res = requests.request(
                method=method,
                url=url,
                json=body,
            )
            if res.status_code != 200:
                raise ValueError(f"Error fetching API json from {url}: {res.status_code}")
            json = res.json()
            return json
        except Exception as e:
            print(f"Error calling API: {e}")
            raise
    
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
