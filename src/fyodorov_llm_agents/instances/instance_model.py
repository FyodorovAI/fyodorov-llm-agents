from pydantic import Field
from typing import Dict, Any, ClassVar
from fyodorov_llm_agents.base_model import FyodorovBaseModel

class InstanceModel(FyodorovBaseModel):
    # Override class constants for title validation
    MAX_TITLE_LENGTH: ClassVar[int] = 80
    
    id: int = Field(None, alias='id')
    agent_id: int  # Links to AgentModel.id
    title: str = ""
    chat_history: list[dict] = []

    def validate(self) -> bool:
        """Validate instance model fields"""
        try:
            if self.title:
                self.validate_text_field(self.title, 'Title', self.MAX_TITLE_LENGTH, required=True)
            return super().validate()
        except ValueError as e:
            print("Instance model validation error:", e)
            return False
        
    def resource_dict(self) -> Dict[str, Any]:
        """Generate resource dictionary for API responses"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'title': self.title,
        }

    def to_dict(self, exclude_none: bool = True, exclude_fields: list = None) -> Dict[str, Any]:
        """Convert instance to dictionary"""
        return super().to_dict(exclude_none=exclude_none, exclude_fields=exclude_fields)