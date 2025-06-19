from langchain.tools import BaseTool
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
from typing import Type
from pydantic import BaseModel, Field, PrivateAttr
from config.settings import settings

class LocationInput(BaseModel):
    query: str = Field(description="Location query to search for (address, city, landmark, etc.)")

class LocationTool(BaseTool):
    name: str = "location_search"
    description: str = "Search for location information, get coordinates, and find nearby places. Useful for geography and navigation queries."
    args_schema: Type[BaseModel] = LocationInput
    type: str = "custom"  # Add a type or tag that matches the expected value

    _geolocator: Nominatim = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._geolocator = Nominatim(user_agent="agentic-ai-mcp")

    def to_dict(self) -> dict:
        """Convert tool to dict format expected by API"""
        return {
            "type": "custom",
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema() if hasattr(self.args_schema, 'model_json_schema') else self.args_schema.schema()
        }

    def _run(self, query: str) -> str:
        """Search for location information"""
        try:
            location = self._geolocator.geocode(query, exactly_one=False, limit=3)
            
            if not location:
                return f"No location found for '{query}'"
                
            results = []
            for i, loc in enumerate(location, 1):
                lat, lon = loc.latitude, loc.longitude
                
                reverse_location = self._geolocator.reverse((lat, lon), exactly_one=True)
                address_components = reverse_location.raw.get('address', {})
                
                location_info = f"""
**{i}. {loc.address}**
📍 **Coordinates:** {lat:.6f}, {lon:.6f}
🏢 **Type:** {address_components.get('amenity', address_components.get('place', 'Location'))}
🌍 **Country:** {address_components.get('country', 'Unknown')}
🏙️ **City:** {address_components.get('city', address_components.get('town', address_components.get('village', 'Unknown')))}
📮 **Postal Code:** {address_components.get('postcode', 'Unknown')}
"""
                results.append(location_info.strip())
                
            return "\n\n".join(results)
            
        except Exception as e:
            return f"Error searching for location: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Async version of location search"""
        return self._run(query)

class DistanceCalculatorInput(BaseModel):
    location1: str = Field(description="First location")
    location2: str = Field(description="Second location")

class DistanceCalculatorTool(BaseTool):
    name: str = "calculate_distance"
    description: str = "Calculate distance between two locations. Useful for travel planning and geography questions."
    args_schema: Type[BaseModel] = DistanceCalculatorInput
    type: str = "custom"  # Add a type or tag that matches the expected value

    _geolocator: Nominatim = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._geolocator = Nominatim(user_agent="agentic-ai-mcp")

    def to_dict(self) -> dict:
        """Convert tool to dict format expected by API"""
        return {
            "type": "custom",
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema() if hasattr(self.args_schema, 'model_json_schema') else self.args_schema.schema()
        }

    def _run(self, location1: str, location2: str) -> str:
        """Calculate distance between two locations"""
        try:
            loc1 = self._geolocator.geocode(location1)
            loc2 = self._geolocator.geocode(location2)
            
            if not loc1:
                return f"Could not find location: {location1}"
            if not loc2:
                return f"Could not find location: {location2}"
                
            coords1 = (loc1.latitude, loc1.longitude)
            coords2 = (loc2.latitude, loc2.longitude)
            
            distance = geodesic(coords1, coords2)
            
            return f"""
**Distance Calculation**
📍 **From:** {loc1.address}
📍 **To:** {loc2.address}
📏 **Distance:** {distance.kilometers:.2f} km ({distance.miles:.2f} miles)
"""
            
        except Exception as e:
            return f"Error calculating distance: {str(e)}"

    async def _arun(self, location1: str, location2: str) -> str:
        """Async version of distance calculation"""
        return self._run(location1, location2)