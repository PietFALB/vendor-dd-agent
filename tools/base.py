from pydantic import BaseModel


class ToolResult(BaseModel):
    ok: bool  
    data: dict | list | None = None
    error: str | None = None
    source: str  # URL or dataset name, cited in the report
