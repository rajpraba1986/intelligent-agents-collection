from langchain.tools import BaseTool
import requests
from typing import Type, Optional
from pydantic import BaseModel, Field
from ..config.settings import settings

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

    def _run(self, location: str, units: str = "metric") -> str:
        """Get weather information"""
        try:
            if not settings.openweather_api_key:
                return "Weather API key not configured. Please set OPENWEATHER_API_KEY environment variable."
                
            # Get coordinates first
            geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct"
            geocoding_params = {
                "q": location,
                "limit": 1,
                "appid": settings.openweather_api_key
            }
            
            geo_response = requests.get(geocoding_url, params=geocoding_params)
            geo_data = geo_response.json()
            
            if not geo_data:
                return f"Location '{location}' not found."
                
            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
            
            # Get weather data
            weather_url = "http://api.openweathermap.org/data/2.5/weather"
            weather_params = {
                "lat": lat,
                "lon": lon,
                "appid": settings.openweather_api_key,
                "units": units
            }
            
            weather_response = requests.get(weather_url, params=weather_params)
            weather_data = weather_response.json()
            
            if weather_response.status_code != 200:
                return f"Error getting weather data: {weather_data.get('message', 'Unknown error')}"
                
            # Format weather information
            main = weather_data["main"]
            weather = weather_data["weather"][0]
            wind = weather_data.get("wind", {})
            
            unit_symbol = "°C" if units == "metric" else "°F" if units == "imperial" else "K"
            wind_unit = "m/s" if units == "metric" else "mph"
            
            weather_info = f"""
**Weather for {weather_data['name']}, {weather_data['sys']['country']}**

🌡️ **Temperature:** {main['temp']}{unit_symbol} (feels like {main['feels_like']}{unit_symbol})
🌤️ **Condition:** {weather['main']} - {weather['description']}
💧 **Humidity:** {main['humidity']}%
🌬️ **Wind:** {wind.get('speed', 'N/A')} {wind_unit}
🔽 **Pressure:** {main['pressure']} hPa
👁️ **Visibility:** {weather_data.get('visibility', 'N/A')} meters
"""
            
            return weather_info.strip()
            
        except Exception as e:
            return f"Error getting weather information: {str(e)}"

    async def _arun(self, location: str, units: str = "metric") -> str:
        """Async version of weather lookup"""
        return self._run(location, units)