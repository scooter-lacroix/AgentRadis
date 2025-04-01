from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class WeatherResponse:
    temperature: float
    conditions: str
    humidity: int
    wind_speed: float
    location: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "conditions": self.conditions,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "location": self.location,
        }


class WeatherToolError(Exception):
    """Base exception for WeatherTool errors"""
    pass


class LocationNotFoundError(WeatherToolError):
    """Raised when location cannot be found"""
    pass


class WeatherTool:
    def __init__(self):
        # Mock weather data for demonstration
        self._mock_data = {
            "new york": WeatherResponse(
                temperature=72.5,
                conditions="Partly Cloudy",
                humidity=65,
                wind_speed=8.5,
                location="New York, NY",
            ),
            "london": WeatherResponse(
                temperature=18.0,
                conditions="Light Rain",
                humidity=80,
                wind_speed=12.0,
                location="London, UK",
            ),
            "tokyo": WeatherResponse(
                temperature=25.0,
                conditions="Clear",
                humidity=70,
                wind_speed=5.0,
                location="Tokyo, Japan",
            ),
        }

    @property
    def name(self) -> str:
        """The name of the tool."""
        return "weather_tool"
        
    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return "Get current weather information for various locations around the world"
        
    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to get weather information for (e.g., 'New York', 'London')"
                }
            },
            "required": ["location"]
        }

    def query_weather(self, location: str) -> Dict[str, Any]:
        """
        Query weather information for a given location.

        Args:
            location: String representing the location to query

        Returns:
            Dictionary containing weather information

        Raises:
            LocationNotFoundError: If the location is not found in the mock data
            WeatherToolError: For other weather-related errors
        """
        try:
            location_key = location.lower().strip()
            if location_key not in self._mock_data:
                raise LocationNotFoundError(
                    f"Weather data not found for location: {location}"
                )

            weather_data = self._mock_data[location_key]
            return {"success": True, "data": weather_data.to_dict(), "error": None}

        except LocationNotFoundError as e:
            return {"success": False, "data": None, "error": str(e)}
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to retrieve weather data: {str(e)}",
            }
            
    async def run(self, **kwargs) -> Any:
        """
        Execute the weather query functionality.
        
        Args:
            location: String representing the location to query for weather information
            
        Returns:
            Dictionary containing weather information or error message
        """
        try:
            location = kwargs.get("location")
            if not location:
                return "Error: Location parameter is required"
                
            result = self.query_weather(location)
            
            if result["success"]:
                data = result["data"]
                return f"Weather for {data['location']}:\n" + \
                       f"Temperature: {data['temperature']}°F\n" + \
                       f"Conditions: {data['conditions']}\n" + \
                       f"Humidity: {data['humidity']}%\n" + \
                       f"Wind Speed: {data['wind_speed']} mph"
            else:
                return f"Error: {result['error']}"
                
        except Exception as e:
            return f"Unexpected error: {str(e)}"
            
    def as_function(self) -> Dict[str, Any]:
        """Get the tool's schema in LLM function format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        
    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        # No resources to clean up for this tool
        pass
        
    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # No state to reset for this tool
        pass
