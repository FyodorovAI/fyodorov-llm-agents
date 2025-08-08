from pydantic import HttpUrl
from typing import Literal, Dict, Any
from fyodorov_llm_agents.base_model import FyodorovBaseModel

Provider = Literal['openai', 'mistral', 'ollama', 'openrouter', 'gemini', 'google']

class ProviderModel(FyodorovBaseModel):
    name: Provider
    api_key: str | None = None
    api_url: HttpUrl | None = None

    def to_dict(self, exclude_none: bool = True, exclude_fields: list = None) -> Dict[str, Any]:
        """Convert provider to dictionary with name lowercased"""
        data = super().to_dict(exclude_none=exclude_none, exclude_fields=exclude_fields)
        
        # Ensure name is lowercase
        if 'name' in data:
            data['name'] = data['name'].lower()
            
        # Convert HttpUrl to string
        if 'api_url' in data and data['api_url'] is not None:
            data['api_url'] = str(data['api_url'])
            
        return data

    def resource_dict(self) -> Dict[str, Any]:
        """Generate resource dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], **kwargs):
        """Create ProviderModel from dictionary with name normalization"""
        processed_data = data.copy()
        
        # Ensure name is lowercase if provided
        if 'name' in processed_data and processed_data['name']:
            processed_data['name'] = processed_data['name'].lower()
            
        return super().from_dict(processed_data, **kwargs)
