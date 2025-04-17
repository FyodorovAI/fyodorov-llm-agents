from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, Literal
import re
from datetime import datetime

APIUrlTypes = Literal['openapi']

# Example regex for validating textual fields; adjust as needed
VALID_CHARACTERS_REGEX = r'^[a-zA-Z0-9\s.,!?:;\'"\-_]+$'
MAX_DISPLAY_NAME_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 1000

class MCPTool(BaseModel):
    """
    Pydantic model corresponding to the 'mcp_tools' table.
    """
    # Database columns
    id: Optional[int] = None                          # bigserial (int8) primary key
    created_at: Optional[datetime] = None             # timestamptz
    updated_at: Optional[datetime] = None             # timestamptz

    display_name: Optional[str] = Field(..., max_length=MAX_DISPLAY_NAME_LENGTH)
    handle: Optional[str] = None
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH)
    logo_url: Optional[str] = None                    # stored as text; could be a URL
    user_id: Optional[str] = None                     # uuid

    public: Optional[bool] = False
    api_type: Optional[str] = None
    api_url: Optional[str] = None                     # stored as text; could also be HttpUrl
    auth_method: Optional[str] = None
    auth_info: Optional[Dict[str, Any]] = None        # jsonb
    capabilities: Optional[Dict[str, Any]] = None     # jsonb
    health_status: Optional[str] = None
    usage_notes: Optional[str] = None

    # Example validations below. Adjust/extend to fit your needs.

    def validate_model_fields(self) -> bool:
        """
        Run custom validations on the model fields.
        Returns True if all validations pass, otherwise raises ValueError.
        """
        if self.display_name:
            self._validate_display_name(self.display_name)
        if self.description:
            self._validate_description(self.description)
        if self.api_url:
            self._validate_url(self.api_url)
        if self.logo_url:
            self._validate_url(self.logo_url)
        # Add more validations as desired...
        return True

    @staticmethod
    def _validate_display_name(name: str) -> None:
        if not re.match(VALID_CHARACTERS_REGEX, name):
            raise ValueError("display_name contains invalid characters.")

    @staticmethod
    def _validate_description(description: str) -> None:
        if not re.match(VALID_CHARACTERS_REGEX, description):
            raise ValueError("description contains invalid characters.")

    @staticmethod
    def _validate_url(url: str) -> None:
        if not HttpUrl.validate(url):
            raise ValueError("{url} is not a valid URL.")

    def to_dict(self) -> dict:
        """
        Convert this Pydantic model to a plain dict (e.g., for inserting into Supabase).
        """
        return self.dict(exclude_none=True)
