from langchain.tools import BaseTool
from duckduckgo_search import DDGS
from typing import Type
from pydantic import BaseModel, Field
from config.settings import settings

class DuckDuckGoSearchInput(BaseModel):
    query: str = Field(description="Search query for DuckDuckGo")
    max_results: int = Field(default=5, description="Maximum number of results to return")

class DuckDuckGoTool(BaseTool):
    name: str = "duckduckgo_search"  # Add type annotation
    description: str = "Search the web for current information using DuckDuckGo. Useful for finding recent news, facts, and general information."  # Add type annotation
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput

    def to_dict(self) -> dict:
        """Convert tool to dict format expected by API"""
        return {
            "type": "custom",
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema() if hasattr(self.args_schema, 'model_json_schema') else self.args_schema.schema()
        }

    def _run(self, query: str, max_results: int = 5) -> str:
        """Execute DuckDuckGo search"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
            if not results:
                return "No search results found."
                
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. **{result.get('title', 'No title')}**\n"
                    f"   URL: {result.get('href', 'No URL')}\n"
                    f"   Summary: {result.get('body', 'No description')}\n"
                )
                
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error performing search: {str(e)}"

    async def _arun(self, query: str, max_results: int = 5) -> str:
        """Async version of the search"""
        return self._run(query, max_results)