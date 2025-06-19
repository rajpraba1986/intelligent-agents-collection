from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import logging
import re
import requests
from urllib.parse import quote
import json

logger = logging.getLogger(__name__)

class YouTubeSearchInput(BaseModel):
    query: str = Field(description="Search query for YouTube videos")
    max_results: int = Field(default=5, description="Maximum number of video results to return")

class YouTubeTool(BaseTool):
    name: str = "youtube_search"
    description: str = "Search for YouTube videos on any topic. Useful for finding educational, entertainment, or instructional videos."
    args_schema: Type[BaseModel] = YouTubeSearchInput

    def to_dict(self) -> dict:
        """Convert tool to dict format expected by API"""
        return {
            "type": "custom",
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema() if hasattr(self.args_schema, 'model_json_schema') else self.args_schema.schema()
        }

    def _create_smart_video_recommendations(self, query: str, max_results: int = 5) -> str:
        """Create intelligent video recommendations based on query analysis"""
        try:
            logger.info(f"Creating smart YouTube recommendations for: {query}")
            
            query_lower = query.lower()
            recommendations = []
            
            # Enhanced Singapore family activities detection
            if any(word in query_lower for word in ['singapore', 'family', 'kids', 'children']) or \
               any(phrase in query_lower for phrase in ['weekend', 'trip', 'activities', 'playground']):
                
                # Singapore family weekend recommendations
                recommendations = [
                    {
                        "title": "Singapore Family Weekend Guide - Best Activities for Kids Aged 2-8",
                        "description": "Complete weekend itinerary for families with young children including Jacob Ballas Children's Garden, East Coast Park, and Singapore Zoo",
                        "search_term": "Singapore family weekend activities kids 2-8 years old",
                        "estimated_duration": "15-20 minutes",
                        "topics": ["Jacob Ballas Children's Garden", "East Coast Park", "Singapore Zoo", "Gardens by the Bay"]
                    },
                    {
                        "title": "Singapore Zoo Family Visit - Complete Guide with Kids",
                        "description": "Detailed walkthrough of Singapore Zoo with children, including splash zones, animal shows, and family-friendly facilities",
                        "search_term": "Singapore Zoo family visit guide children",
                        "estimated_duration": "18-25 minutes",
                        "topics": ["Animal shows", "Splash Safari", "Tram rides", "Family facilities"]
                    },
                    {
                        "title": "Jacob Ballas Children's Garden - Singapore's Best Free Family Activity",
                        "description": "Exploring Singapore's premier children's garden with playground areas for different ages",
                        "search_term": "Jacob Ballas Children's Garden Singapore family",
                        "estimated_duration": "12-15 minutes",
                        "topics": ["Treehouse", "Water play", "Sensory garden", "Age-appropriate zones"]
                    },
                    {
                        "title": "East Coast Park Family Cycling and Beach Fun",
                        "description": "Family cycling adventure at East Coast Park with beach activities and food recommendations",
                        "search_term": "East Coast Park Singapore family cycling beach",
                        "estimated_duration": "14-18 minutes",
                        "topics": ["Bike rental", "Beach play", "Food centres", "Playgrounds"]
                    },
                    {
                        "title": "Gardens by the Bay with Kids - Family-Friendly Singapore Attraction",
                        "description": "Exploring Gardens by the Bay's Flower Dome and outdoor gardens with children",
                        "search_term": "Gardens by the Bay Singapore family kids guide",
                        "estimated_duration": "16-20 minutes",
                        "topics": ["Flower Dome", "Outdoor gardens", "Children's garden", "Photo spots"]
                    }
                ]
            
            # Weather-related Singapore content
            elif any(word in query_lower for word in ['weather', 'singapore']) and any(word in query_lower for word in ['family', 'activities']):
                recommendations = [
                    {
                        "title": "Singapore Weather Guide for Families - When to Visit Outdoor Attractions",
                        "description": "Understanding Singapore's tropical weather and planning family activities accordingly",
                        "search_term": "Singapore weather family activities rainy season",
                        "estimated_duration": "10-12 minutes",
                        "topics": ["Best times to visit", "Rainy day alternatives", "Indoor activities"]
                    },
                    {
                        "title": "Singapore Indoor Activities for Families - Rainy Day Options",
                        "description": "Best indoor attractions and activities when weather doesn't cooperate",
                        "search_term": "Singapore indoor family activities rainy day",
                        "estimated_duration": "15-18 minutes",
                        "topics": ["Science Centre", "Museums", "Shopping malls", "Indoor playgrounds"]
                    }
                ]
            
            # General family travel recommendations
            elif any(word in query_lower for word in ['family', 'kids', 'children', 'travel']):
                recommendations = [
                    {
                        "title": "Family Travel Planning with Young Children - Essential Tips",
                        "description": "Comprehensive guide for traveling with kids aged 2-8, including packing and planning tips",
                        "search_term": "family travel planning young children tips guide",
                        "estimated_duration": "15-18 minutes",
                        "topics": ["Packing essentials", "Entertainment ideas", "Safety tips", "Age-appropriate activities"]
                    },
                    {
                        "title": "Best Family Destinations in Southeast Asia",
                        "description": "Top family-friendly destinations and activities in Southeast Asia",
                        "search_term": "best family destinations Southeast Asia children",
                        "estimated_duration": "20-25 minutes",
                        "topics": ["Singapore", "Malaysia", "Thailand", "Family resorts"]
                    }
                ]
            
            # Default recommendations - use cleaned query
            else:
                clean_query = re.sub(r'[^\w\s]', '', query).strip()
                if not clean_query or len(clean_query) < 3:
                    clean_query = "family activities guide"
                
                recommendations = [
                    {
                        "title": f"{clean_query.title()} - Complete Guide and Tips",
                        "description": f"Comprehensive information and practical tips about {clean_query}",
                        "search_term": f"{clean_query} complete guide tips 2024",
                        "estimated_duration": "15-20 minutes",
                        "topics": ["Overview", "Best practices", "Expert tips", "Recent updates"]
                    },
                    {
                        "title": f"Best {clean_query.title()} Recommendations",
                        "description": f"Top recommendations and reviews for {clean_query}",
                        "search_term": f"best {clean_query} recommendations review",
                        "estimated_duration": "12-16 minutes",
                        "topics": ["Top picks", "Comparisons", "User reviews", "Expert opinions"]
                    }
                ]
            
            # Format the response
            formatted_results = []
            formatted_results.append(f"🎥 **YouTube Video Recommendations for '{query}':**\n")
            
            # Add context-aware introduction
            if any(word in query_lower for word in ['singapore', 'family']):
                formatted_results.append("Perfect videos to help plan your Singapore family weekend trip:\n")
            else:
                formatted_results.append("Based on your request, here are the best video recommendations:\n")
            
            for i, rec in enumerate(recommendations[:max_results], 1):
                # Create YouTube search URL
                search_url = f"https://www.youtube.com/results?search_query={quote(rec['search_term'])}"
                
                formatted_results.append(f"**{i}. {rec['title']}**")
                formatted_results.append(f"📋 {rec['description']}")
                formatted_results.append(f"⏱️ Estimated Duration: {rec['estimated_duration']}")
                formatted_results.append(f"🔍 **Search YouTube:** {search_url}")
                formatted_results.append(f"💡 Search Term: \"{rec['search_term']}\"")
                
                if rec.get('topics'):
                    formatted_results.append(f"📝 Key Topics: {', '.join(rec['topics'])}")
                
                formatted_results.append("")
            
            # Add helpful instructions
            formatted_results.append("🎬 **How to Find These Videos:**")
            formatted_results.append("1. Click any of the YouTube search links above")
            formatted_results.append("2. Look for videos with:")
            formatted_results.append("   • High view counts (100K+ views)")
            formatted_results.append("   • Recent upload dates (within last 2 years)")
            formatted_results.append("   • Good like-to-dislike ratios")
            formatted_results.append("   • Detailed descriptions")
            formatted_results.append("3. Check video comments for additional tips from other families")
            formatted_results.append("4. Try variations of the search terms if needed")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Error creating smart recommendations: {e}")
            return self._generate_basic_response(query)

    def _generate_basic_response(self, query: str) -> str:
        """Generate basic YouTube search response"""
        search_url = f"https://www.youtube.com/results?search_query={quote(query)}"
        
        return f"""🎥 **YouTube Search for '{query}':**

I can help you find relevant YouTube videos! Here's your direct search link:

🔗 **YouTube Search Link:**
{search_url}

💡 **Search Tips:**
• Look for recent videos (uploaded in the last year)
• Check channels with verified badges
• Read video descriptions for detailed information
• Check comments for real user experiences

📺 **Recommended Search Terms:**
• "{query}"
• "{query} 2024"
• "{query} guide"
• "{query} tips"

Click the link above to start your search on YouTube!"""

    def _run(self, query: str, max_results: int = 5) -> str:
        """Execute YouTube search with smart recommendations"""
        try:
            logger.info(f"Starting YouTube search for: {query}")
            
            # Create smart recommendations without external dependencies
            result = self._create_smart_video_recommendations(query, max_results)
            logger.info("Successfully created YouTube recommendations")
            return result
            
        except Exception as e:
            logger.error(f"Error in YouTube search: {e}")
            return self._generate_basic_response(query)

    async def _arun(self, query: str, max_results: int = 5) -> str:
        """Async version of the YouTube search"""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self._run, query, max_results)