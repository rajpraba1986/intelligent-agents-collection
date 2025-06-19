from langchain.tools import BaseTool
import requests
from typing import Type, Optional
from pydantic import BaseModel, Field
from config.settings import settings
import re
import logging

logger = logging.getLogger(__name__)

class WeatherInput(BaseModel):
    location: str = Field(description="City name or location to get weather for")
    units: str = Field(default="metric", description="Temperature units: metric (Celsius), imperial (Fahrenheit), or kelvin")

class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "Get current weather information for a specified location. Useful for weather forecasts and current conditions."
    args_schema: Type[BaseModel] = WeatherInput

    def to_dict(self) -> dict:
        """Convert tool to dict format expected by API"""
        return {
            "type": "custom",
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema() if hasattr(self.args_schema, 'model_json_schema') else self.args_schema.schema()
        }

    def _run(self, location: str) -> str:
        """Execute weather lookup with enhanced location handling"""
        try:
            logger.info(f"Getting weather for: {location}")
            
            # Clean and validate location
            clean_location = self._clean_location(location)
            logger.info(f"Cleaned location: {clean_location}")
            
            if settings.openweather_api_key:
                return self._get_weather_with_api(clean_location)
            else:
                return self._get_weather_without_api(clean_location)
                
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return f"I encountered an error getting weather information for {location}. Please try again or check the location name."

    def _clean_location(self, location: str) -> str:
        """Clean and standardize location name"""
        # Remove common suffixes and clean up
        clean_location = location.strip()
        
        # Remove common trailing phrases
        suffixes_to_remove = [
            '. advise on weather forecast',
            '. advise on whether forecast', 
            '. advice on weather',
            '. tell me about weather',
            '. weather information',
            '. forecast',
            '. weather',
            '. today',
            '. now'
        ]
        
        location_lower = clean_location.lower()
        for suffix in suffixes_to_remove:
            if location_lower.endswith(suffix):
                clean_location = clean_location[:len(clean_location)-len(suffix)].strip()
                break
        
        # Remove punctuation at the end
        clean_location = re.sub(r'[.,;:!?]+$', '', clean_location).strip()
        
        # Handle common location variations
        location_mapping = {
            'sg': 'Singapore',
            'singapore': 'Singapore',
            'ny': 'New York',
            'nyc': 'New York City',
            'la': 'Los Angeles',
            'sf': 'San Francisco',
            'uk': 'United Kingdom',
            'usa': 'United States',
            'us': 'United States'
        }
        
        clean_lower = clean_location.lower()
        if clean_lower in location_mapping:
            clean_location = location_mapping[clean_lower]
        
        return clean_location

    def _get_weather_with_api(self, location: str) -> str:
        """Get weather data using OpenWeatherMap API"""
        try:
            # Get coordinates first
            geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct"
            geocoding_params = {
                'q': location,
                'limit': 1,
                'appid': settings.openweather_api_key
            }
            
            geo_response = requests.get(geocoding_url, params=geocoding_params, timeout=10)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            if not geo_data:
                return f"Location '{location}' not found. Please check the spelling or try a more specific location name."
            
            lat, lon = geo_data[0]['lat'], geo_data[0]['lon']
            location_name = geo_data[0].get('name', location)
            country = geo_data[0].get('country', '')
            
            # Get weather data
            weather_url = "http://api.openweathermap.org/data/2.5/weather"
            weather_params = {
                'lat': lat,
                'lon': lon,
                'appid': settings.openweather_api_key,
                'units': 'metric'
            }
            
            weather_response = requests.get(weather_url, params=weather_params, timeout=10)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            # Format weather information
            temp = weather_data['main']['temp']
            feels_like = weather_data['main']['feels_like']
            humidity = weather_data['main']['humidity']
            description = weather_data['weather'][0]['description'].title()
            
            # Optional additional data
            wind_speed = weather_data.get('wind', {}).get('speed', 'N/A')
            pressure = weather_data['main'].get('pressure', 'N/A')
            visibility = weather_data.get('visibility', 0) / 1000 if weather_data.get('visibility') else 'N/A'
            
            response = f"**Current Weather in {location_name}"
            if country:
                response += f", {country}"
            response += ":**\n\n"
            
            response += f"🌡️ **Temperature:** {temp}°C (feels like {feels_like}°C)\n"
            response += f"☁️ **Conditions:** {description}\n"
            response += f"💧 **Humidity:** {humidity}%\n"
            
            if wind_speed != 'N/A':
                response += f"💨 **Wind Speed:** {wind_speed} m/s\n"
            if pressure != 'N/A':
                response += f"🔽 **Pressure:** {pressure} hPa\n"
            if visibility != 'N/A':
                response += f"👁️ **Visibility:** {visibility} km\n"
            
            # Add weather-based recommendations
            if temp > 30:
                response += "\n🔥 **Hot weather tips:**\n"
                response += "• Stay hydrated and seek shade\n"
                response += "• Plan indoor activities during midday\n"
                response += "• Wear light, breathable clothing"
            elif temp < 10:
                response += "\n🧥 **Cold weather tips:**\n"
                response += "• Dress in warm layers\n" 
                response += "• Limit outdoor exposure\n"
                response += "• Check for winter weather advisories"
            elif 'rain' in description.lower():
                response += "\n☔ **Rainy weather tips:**\n"
                response += "• Carry an umbrella or raincoat\n"
                response += "• Consider indoor activities\n"
                response += "• Allow extra travel time"
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return f"Unable to connect to weather service for {location}. Please check your internet connection and try again."
        except KeyError as e:
            logger.error(f"Unexpected API response format: {e}")
            return f"Received unexpected weather data format for {location}. Please try again later."

    def _get_weather_without_api(self, location: str) -> str:
        """Provide weather information without API (fallback)"""
        # Common locations with general info
        location_lower = location.lower()
        
        if 'singapore' in location_lower:
            return """**Weather Information for Singapore:**

🌡️ **Typical Climate:** Tropical (Hot & Humid)
📅 **Year-round:** 25-31°C (77-88°F) 
☔ **Rainy Season:** November to January, June to July
🌤️ **Best Outdoor Hours:** Early morning (7-10 AM) or evening (6-8 PM)

**Current Status:** Unable to get real-time data without API key.

**General Recommendations:**
• Always carry an umbrella (sudden tropical showers)
• Stay hydrated, especially with children
• Plan indoor activities for midday heat
• Early morning is best for outdoor family activities"""

        else:
            return f"""**Weather Information for {location}:**

❌ **Real-time weather data unavailable** - No API key configured.

**To get current weather:**
1. Check a weather app on your phone
2. Visit weather.com or local weather services
3. Search "{location} weather" in your browser

**General Tips:**
• Check local weather before planning outdoor activities
• Have indoor backup plans ready
• Dress appropriately for seasonal conditions
• Stay informed about weather warnings in your area"""

    async def _arun(self, location: str, units: str = "metric") -> str:
        """Async version of weather lookup"""
        return self._run(location)