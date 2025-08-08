from datetime import datetime
import os
import asyncio
from typing import Dict, Any, List, Optional
import litellm
import requests

from fyodorov_utils.config.service_discovery import get_service_url
from fyodorov_llm_agents.base_service import BaseService
from fyodorov_llm_agents.agents.agent_model import Agent as AgentModel
from fyodorov_llm_agents.tools.mcp_tool_service import MCPTool as ToolService
from fyodorov_llm_agents.models.llm_service import LLM


class AgentService(BaseService[AgentModel]):
    def __init__(self):
        super().__init__("agents")
        
    def _dict_to_model(self, data: Dict[str, Any]) -> AgentModel:
        """Convert dictionary from database to AgentModel"""
        return AgentModel.from_dict(data)
    
    def _model_to_dict(self, model: AgentModel) -> Dict[str, Any]:
        """Convert AgentModel to dictionary for database"""
        return model.to_dict()
        
    async def create_agent_in_db(self, access_token: str, agent: AgentModel, user_id: str = None) -> AgentModel:
        """Create agent in database using base service method"""
        agent.validate()
        return await self.create_in_db(agent, access_token, user_id)
        
    async def update_agent_in_db(self, id: str, update_data: Dict[str, Any], access_token: Optional[str] = None) -> AgentModel:
        """Update agent in database"""
        return await self.update_in_db(id, update_data, access_token)
        
    async def delete_agent_in_db(self, id: str, access_token: Optional[str] = None) -> bool:
        """Delete agent from database"""
        return await self.delete_in_db(id, access_token)
        
    async def get_agent_in_db(self, id: str, access_token: Optional[str] = None) -> Optional[AgentModel]:
        """Get agent by ID with model loading"""
        agent = await self.get_in_db(id, access_token)
        if agent and hasattr(agent, 'model_id') and agent.model_id:
            # Load the associated model
            try:
                agent.model = await LLM.get_model(id=agent.model_id)
            except Exception as e:
                print(f"Error loading model for agent {id}: {e}")
        return agent
        
    async def get_agents_in_db(
        self,
        limit: int = 10,
        created_at_lt: datetime = None,
        user_id: str = None,
        access_token: Optional[str] = None
    ) -> List[AgentModel]:
        """Get agents with optional filtering"""
        if created_at_lt is None:
            created_at_lt = datetime.now()
            
        # Use custom filters for public agents if no user_id is provided
        filters = None
        if user_id is None:
            filters = {"public": True}
            
        return await self.get_all_in_db(limit, created_at_lt, user_id, filters, access_token)

    async def save_from_dict(self, access_token: str, user_id: str, agent_dict: Dict[str, Any]) -> AgentModel:
        """Create agent from dictionary data"""
        agent = await AgentModel.from_dict(agent_dict, user_id)
        print("Saving agent", agent)
        return await self.create_agent_in_db(access_token, agent, user_id)

    async def get_agent_tools(self, access_token: str, agent_id: str) -> List[Dict[str, Any]]:
        """Get tools assigned to an agent"""
        if not agent_id:
            raise ValueError("Agent ID is required")
        
        supabase = self.get_supabase_client(access_token)
        result = (
            supabase.table("agent_mcp_tools")
            .select("*")
            .eq("agent_id", agent_id)
            .execute()
        )
        tool_ids = [
            item["mcp_tool_id"] for item in result.data if "mcp_tool_id" in item
        ]
        
        result = []
        for tool_id in tool_ids:
            tool = (
                supabase.table("mcp_tools")
                .select("*")
                .eq("id", tool_id)
                .limit(1)
                .execute()
            )
            if tool and tool.data:
                tool_dict = tool.data[0]
                tool_dict["id"] = str(tool_dict["id"])
                result.append(tool_dict)
        return result

    async def assign_agent_tools(
        self, access_token: str, agent_id: str, tool_ids: List[str]
    ) -> List[str]:
        """Assign tools to an agent"""
        if not tool_ids:
            raise ValueError("Tool IDs are required")
            
        supabase = self.get_supabase_client(access_token)
        result = []
        
        for tool_id in tool_ids:
            # Check if tool is valid and exists in the database
            tool_result = (
                supabase.table("mcp_tools")
                .select("*")
                .eq("id", tool_id)
                .limit(1)
                .execute()
            )
            if not tool_result.data:
                print(f"Tool with ID {tool_id} does not exist.")
                continue
                
            supabase.table("agent_mcp_tools").insert(
                {"mcp_tool_id": tool_id, "agent_id": agent_id}
            ).execute()
            print("Inserted tool", tool_id, "for agent", agent_id)
            result.append(tool_id)
        return result

    async def delete_agent_tool_connection(
        self, access_token: str, agent_id: str, tool_id: str
    ) -> bool:
        """Remove tool connection from an agent"""
        if not agent_id:
            raise ValueError("Agent ID is required")
        if not tool_id:
            raise ValueError("Tool ID is required")
            
        try:
            supabase = self.get_supabase_client(access_token)
            supabase.table("agent_mcp_tools").delete().eq("agent_id", agent_id).eq(
                "mcp_tool_id", tool_id
            ).execute()
            return True
        except Exception as e:
            print("Error deleting agent tool", str(e))
            raise e


class Agent(AgentModel):
    """Legacy wrapper class for backward compatibility - extends AgentModel with runtime functionality"""
    
    def __init__(self, agent: AgentModel):
        super().__init__(**agent.to_dict())

    async def call_with_fn_calling(
        self, input: str = "", history=[], user_id: str = ""
    ) -> dict:
        """Execute agent with function calling capabilities"""
        print("call_with_fn_calling")
        litellm.set_verbose = True
        # Set environmental variable
        print(f"[call_with_fn_calling] self.model: {self.model}")

        if self.provider:
            self.api_key = self.provider.api_key
            self.api_url = self.provider.api_url
            if self.provider.name == "gemini":
                model = "gemini/" + self.model.name
                os.environ["GEMINI_API_KEY"] = self.api_key
        elif self.api_key.startswith("sk-"):
            model = "openai/" + self.model.name
            os.environ["OPENAI_API_KEY"] = self.api_key
            self.api_url = "https://api.openai.com/v1"
        elif self.api_key and self.api_key != "":
            model = "mistral/" + self.model.name
            os.environ["MISTRAL_API_KEY"] = self.api_key
            self.api_url = "https://api.mistral.ai/v1"
        else:
            print("Provider Ollama")
            model = "ollama/" + self.model.name
            if self.api_url is None:
                self.api_url = "https://api.ollama.ai/v1"

        base_url = str(self.api_url).rstrip("/")
        messages: list[dict] = [
            {"content": self.prompt, "role": "system"},
            *history,
            {"content": input, "role": "user"},
        ]
        
        # Load tools
        print(f"Tools: {self.tools}")
        mcp_tools = []
        for tool in self.tools:
            try:
                tool_instance = await ToolService.get_by_handle(tool)
                mcp_tools.append(tool_instance)
            except Exception as e:
                print(f"Error fetching tool {tool}: {e}")

        tool_schemas = [tool.get_function() for tool in mcp_tools]
        print(f"Tool schemas: {tool_schemas}")
        
        if tool_schemas:
            print(
                f"calling litellm with model {model}, messages: {messages}, max_retries: 0, history: {history}, base_url: {base_url}, tools: {tool_schemas}"
            )
            response = litellm.completion(
                model=model, messages=messages, max_retries=0, base_url=base_url
            )
        else:
            print(
                f"calling litellm with model {model}, messages: {messages}, max_retries: 0, history: {history}, base_url: {base_url}"
            )
            response = litellm.completion(
                model=model, messages=messages, max_retries=0, base_url=base_url
            )
        print(f"Response: {response}")

        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            args = tool_call.function.arguments

            # Find the corresponding tool
            mcp_tool = None
            for tool in mcp_tools:
                function_def = tool.get_function()
                if function_def["name"] == function_name:
                    mcp_tool = tool
                    break

            # Forward tool call to Tsiolkovsky instead of calling locally
            tool_output = await self._forward_tool_call_to_tsiolkovsky(
                mcp_tool.id, args, user_id  # Using user_id instead of undefined user_session
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                }
            )

            followup = litellm.completion(
                model=model,
                messages=messages,
                max_retries=0,
                base_url=base_url,
            )
            return {"answer": followup.choices[0].message.content}

        answer = message.content
        print(f"Answer: {answer}")
        return {
            "answer": answer,
        }

    async def _forward_tool_call_to_tsiolkovsky(
        self, tool_id: str, args: str, user_session: str
    ) -> str:
        """Forward function call to Tsiolkovsky for execution"""
        try:
            tsiolkovsky_url = get_service_url("Tsiolkovsky")

            response = await asyncio.to_thread(
                requests.post,
                f"{tsiolkovsky_url}/tools/{tool_id}/call",
                json={"args": args},
                headers={"Authorization": f"Bearer {user_session}"},
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("result", "")
            else:
                return f"Error calling tool: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error forwarding tool call: {str(e)}"