from langchain.tools import BaseTool
from youtubesearchpython import VideosSearch
from typing import Type
from pydantic import BaseModel, Field

class YouTubeSearchInput(BaseModel):
    query: str = Field(description="Search query for YouTube videos")
    max_results: int = Field(default=5, description="Maximum number of video results to return")

class YouTubeTool(BaseTool):
    name: str = "youtube_search"  # Add type annotation
    description: str = "Search for YouTube videos on any topic. Useful for finding educational, entertainment, or instructional videos."  # Add type annotation
    args_schema: Type[BaseModel] = YouTubeSearchInput

    def to_dict(self) -> dict:
        """Convert tool to dict format expected by API"""
        return {
            "type": "custom",
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema() if hasattr(self.args_schema, 'model_json_schema') else self.args_schema.schema()
        }

    def _run(self, query: str, max_results: int = 5) -> str:
        """Execute YouTube search"""
        try:
            videos_search = VideosSearch(query, limit=max_results)
            results = videos_search.result()
            
            if not results.get('result'):
                return "No YouTube videos found."
                
            formatted_results = []
            for i, video in enumerate(results['result'], 1):
                duration = video.get('duration', 'Unknown duration')
                views = video.get('viewCount', {}).get('text', 'Unknown views')
                channel = video.get('channel', {}).get('name', 'Unknown channel')
                
                formatted_results.append(
                    f"{i}. **{video.get('title', 'No title')}**\n"
                    f"   Channel: {channel}\n"
                    f"   Duration: {duration}\n"
                    f"   Views: {views}\n"
                    f"   URL: {video.get('link', 'No URL')}\n"
                    f"   Description: {video.get('descriptionSnippet', [{}])[0].get('text', 'No description') if video.get('descriptionSnippet') else 'No description'}\n"
                )
                
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"Error searching YouTube: {str(e)}"

    async def _arun(self, query: str, max_results: int = 5) -> str:
        """Async version of the search"""
        return self._run(query, max_results)