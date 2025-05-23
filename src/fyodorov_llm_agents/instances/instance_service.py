from datetime import datetime
from supabase import Client
from fyodorov_utils.config.supabase import get_supabase

from fyodorov_llm_agents.providers.provider_service import Provider
from fyodorov_llm_agents.agents.agent_model import Agent as AgentModel
from fyodorov_llm_agents.models.llm_model import LLMModel
from fyodorov_llm_agents.models.llm_service import LLM
from fyodorov_llm_agents.agents.agent_service import Agent
from fyodorov_llm_agents.tools.mcp_tool_service import MCPTool as ToolService

from .instance_model import InstanceModel

supabase: Client = get_supabase()

JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6Im14MmVrTllBY3ZYN292LzMiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzA3MzI0MTMxLCJpYXQiOjE3MDczMjA1MzEsImlzcyI6Imh0dHBzOi8vbGptd2R2ZWZrZ3l4cnVjc2dla3cuc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6IjljYzYzOWQ0LWUwMzItNDM3Zi1hNWVhLTUzNDljZGE0YTNmZCIsImVtYWlsIjoiZGFuaWVsQGRhbmllbHJhbnNvbS5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7Imludml0ZV9jb2RlIjoiUkFOU09NIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3MDczMjA1MzF9XSwic2Vzc2lvbl9pZCI6ImE4MTM4NmE1LTUxZTUtNDkyMS04ZjM3LWMyYWE3ODlhZDRhZiJ9.NNZA2rm1IQQ9wAhpyC8taMqregRmy8I9oZgT0P5heBg"

class Instance(InstanceModel):

    async def chat_w_fn_calls(self, input: str = "", access_token: str = JWT, user_id: str = "") -> str:
        agent: AgentModel = await Agent.get_in_db(id = self.agent_id)
        print(f"Model fetched via LLM.get_model in chat_w_fn_calls: {agent.model}")
        agent.provider = await Provider.get_provider_by_id(id = agent.model.provider)
        agent.prompt = f"{agent.prompt}\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        print(f"Iterating over agent tools in chat_w_fn_calls: {agent.tools}")
        for index, tool in enumerate(agent.tools):
            if isinstance(tool, str):
                agent.tools[index] = await ToolService.get_by_name_and_user_id(access_token, tool, user_id)
                print(f"Tool fetched via Tool.get_by_name_and_user_id in chat_w_fn_calls: {agent.tools[index]}")
                agent.prompt += f"\n\n{agent.tools[index].handle}: {agent.tools[index].description}\n\n"
        agent_service = Agent(agent)
        res = await agent_service.call_with_fn_calling(input=input, history=self.chat_history, user_id=user_id)
        self.chat_history.append({
            "role": "user",
            "content": input
        })
        self.chat_history.append({
            "role": "assistant",
            "content": res["answer"]
        })
        # Update history
        await self.create_in_db(instance=self)
        return res

    @staticmethod
    async def create_in_db(instance: InstanceModel) -> dict:
        try:
            existing_instance = await Instance.get_by_title_and_agent(instance.title, instance.agent_id)
            if existing_instance:
                needs_update = False
                for key, value in instance.to_dict().items():
                    if value != existing_instance[key]:
                        print(f"Instance {key} needs updating: {value} != {existing_instance[key]}")
                        needs_update = True
                        existing_instance[key] = value
                if needs_update:
                    print('Instance already exists, will update:', existing_instance)
                    instance = await Instance.update_in_db(existing_instance["id"], existing_instance)
                else:
                    print('Instance already exists and no update needed:', existing_instance)
                    instance = InstanceModel(**existing_instance)
            else:
                print("Creating instance in DB:", instance.to_dict())
                result = supabase.table('instances').upsert(instance.to_dict()).execute()
                if not result or not result.data:
                    print(f"Error creating instance in DB: {result}")
                    raise ValueError('Error creating instance in DB')
                print(f"Result of creating instance in DB: {result}")
                instance_dict = result.data[0]
                instance_dict['title'] = f"{instance_dict['title']} {instance_dict['id']}"
                instance = await Instance.update_in_db(instance_dict['id'], instance_dict)
            return instance
        except Exception as e:
            print(f"An error occurred while creating instance: {e}")
            if 'code' in e and e.code == '23505':
                print('Instance already exists')
                instance = await Instance.get_by_title_and_agent(instance.title, instance.agent_id)
                return instance
            print('Error creating instance', str(e))
            raise e

    @staticmethod
    async def update_in_db(id: str, instance: dict) -> InstanceModel:
        if not id:
            raise ValueError('Instance ID is required')
        try:
            print(f"Updating instance in DB with ID: {id}, data: {instance}")
            result = supabase.table('instances').update(instance).eq('id', id).execute()
            print(f"Result of update: {result}")
            instance_dict = result.data[0]
            return instance_dict
        except Exception as e:
            print('An error occurred while updating instance:', id, str(e))
            raise

    @staticmethod
    async def delete_in_db(id: str) -> bool:
        if not id:
            raise ValueError('Instance ID is required')
        try:
            result = supabase.table('instances').delete().eq('id', id).execute()
            print('Deleted instance', result)
            if not result.data:
                raise ValueError('Instance ID not found')
            else:
                return True
        except Exception as e:
            print('Error deleting instance', str(e))
            raise e

    @staticmethod
    async def get_by_title_and_agent(title: str, agent_id: str) -> InstanceModel:
        if not title:
            raise ValueError('Instance title is required')
        if not agent_id:
            raise ValueError('Agent ID is required')
        try:
            print(f"Fetching instance with title {title} and agent ID {agent_id}")
            result = supabase.table('instances').select('*').eq('title', title).eq('agent_id', agent_id).limit(1).execute()
            if not result or not result.data:
                print(f"No instance found with the given title {title} and agent ID {agent_id}: {result}")
                return None
            instance_dict = result.data[0]
            print(f"Fetched instance: {instance_dict}")
            return InstanceModel(**instance_dict)
        except Exception as e:
            print('[Instance.get_by_title_and_agent] Error fetching instance', str(e))
            raise e

    @staticmethod
    async def get_in_db(id: int) -> InstanceModel:
        if not id:
            raise ValueError('Instance ID is required')
        try:
            result = supabase.table('instances').select('*').eq('id', id).limit(1).execute()
            instance_dict = result.data[0]
            print(f"Fetched instance: {instance_dict}")
            instance = InstanceModel(**instance_dict)
            return instance
        except Exception as e:
            print('[Instance.get_in_db] Error fetching instance', str(e))
            raise e

    @staticmethod
    async def get_all_in_db(limit: int = 10, created_at_lt: datetime = datetime.now(), user_id: str = None) -> list[InstanceModel]:
        try:
            supabase = get_supabase()
            agents = await Agent.get_all_in_db(limit=limit, created_at_lt=created_at_lt, user_id=user_id)
            if not agents:
                print("No agents found")
                return []
            agent_ids = [agent.id for agent in agents]
            print(f"Agent IDs: {agent_ids}")
            if not agent_ids:
                print("No agent IDs found")
                return []
            instances = []
            for agent in agents:
                result = supabase.from_('instances') \
                    .select("*") \
                    .eq('agent_id', agent.id) \
                    .limit(limit) \
                    .lt('created_at', created_at_lt) \
                    .order('created_at', desc=True) \
                    .execute()
                if not result.data:
                    continue
                instance_models = [InstanceModel(**instance) for instance in result.data]
                instances.extend(instance_models)
            return instances
        except Exception as e:
            print('[Instance.get_all_in_db] Error fetching instances', str(e))
            raise e