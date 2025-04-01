#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
import json
import asyncio
from typing import Dict, Any, List, Optional, Union

from app.tool.enhanced_tool import CacheableTool, cacheable

class HeavyComputationTool(CacheableTool):
    """Demo tool that simulates heavy computation with caching."""
    
    def __init__(self, cache_ttl: int = 60):
        """Initialize the HeavyComputationTool."""
        super().__init__(cache_ttl=cache_ttl)
        
    @property
    def name(self) -> str:
        return "heavy_computation"
        
    @property
    def description(self) -> str:
        return "Performs an expensive computation with input parameters."
        
    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "input_value": {"type": "number"},
                "complexity": {"type": "integer", "minimum": 1, "maximum": 10}
            },
            "required": ["input_value"]
        }
        
    @cacheable(ttl=120)  # Cache results for 2 minutes
    def run(self, input_value: float, complexity: int = 5) -> Dict[str, Any]:
        """
        Run a simulated expensive computation.
        
        Args:
            input_value: The primary input value
            complexity: How complex (and slow) the operation should be (1-10)
            
        Returns:
            Computation results
        """
        # Simulate computation time based on complexity
        computation_time = 0.2 * complexity
        time.sleep(computation_time)
        
        # Simulated computation result
        result = {
            "input": input_value,
            "complexity": complexity,
            "result": input_value * (1 + random.random() * complexity),
            "computation_time": computation_time,
            "timestamp": time.time()
        }
        
        return result


class AsyncWeatherTool(CacheableTool):
    """Demo tool that simulates async weather API calls with caching."""
    
    def __init__(self, cache_ttl: int = 300):
        """Initialize the AsyncWeatherTool."""
        super().__init__(cache_ttl=cache_ttl)
        # Simulated weather data
        self._weather_data = {
            "New York": {"temp": 20, "humidity": 65, "conditions": "Cloudy"},
            "London": {"temp": 15, "humidity": 80, "conditions": "Rainy"},
            "Tokyo": {"temp": 25, "humidity": 70, "conditions": "Sunny"},
            "Sydney": {"temp": 22, "humidity": 60, "conditions": "Clear"}
        }
        
    @property
    def name(self) -> str:
        return "weather"
        
    @property
    def description(self) -> str:
        return "Get current weather information for a location."
        
    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "units": {"type": "string", "enum": ["metric", "imperial"]}
            },
            "required": ["location"]
        }
        
    @cacheable(ttl=600)  # Cache weather for 10 minutes
    async def run(self, location: str, units: str = "metric") -> Dict[str, Any]:
        """
        Get weather information for a location.
        
        Args:
            location: City name
            units: Temperature units (metric/imperial)
            
        Returns:
            Weather information
        """
        # Simulate network delay
        await asyncio.sleep(1)
        
        # Check if location exists in our simulated data
        location_key = next((k for k in self._weather_data.keys() 
                           if k.lower() == location.lower()), None)
        
        if not location_key:
            return {
                "error": f"Location '{location}' not found",
                "timestamp": time.time()
            }
            
        # Get base weather data
        weather = self._weather_data[location_key]
        
        # Convert temperature if needed
        temp = weather["temp"]
        if units == "imperial":
            temp = (temp * 9/5) + 32
            temp_unit = "°F"
        else:
            temp_unit = "°C"
            
        # Add some randomness to simulate changing weather
        temp_variation = random.uniform(-1.0, 1.0)
        
        return {
            "location": location_key,
            "temperature": round(temp + temp_variation, 1),
            "temperature_unit": temp_unit,
            "humidity": weather["humidity"],
            "conditions": weather["conditions"],
            "units": units,
            "timestamp": time.time()
        }


class DataAggregateTool(CacheableTool):
    """Demo tool that depends on other tools and aggregates their results."""
    
    def __init__(self, weather_tool: AsyncWeatherTool, computation_tool: HeavyComputationTool):
        """
        Initialize the DataAggregateTool.
        
        Args:
            weather_tool: Instance of AsyncWeatherTool
            computation_tool: Instance of HeavyComputationTool
        """
        super().__init__(cache_ttl=60)  # Short cache time for aggregated data
        self.weather_tool = weather_tool
        self.computation_tool = computation_tool
        
    @property
    def name(self) -> str:
        return "data_aggregate"
        
    @property
    def description(self) -> str:
        return "Aggregates data from multiple sources including weather and computations."
        
    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "input_value": {"type": "number"}
            },
            "required": ["location", "input_value"]
        }
        
    @cacheable(ttl=120)
    async def run(self, location: str, input_value: float) -> Dict[str, Any]:
        """
        Aggregate data from multiple sources.
        
        Args:
            location: Location for weather data
            input_value: Input for computation
            
        Returns:
            Aggregated data from multiple sources
        """
        # Get weather data (using the cached version if available)
        weather_data = await self.weather_tool.run(location)
        
        # Apply a computation based on weather and input
        # Use the input_value adjusted by temperature
        adjusted_input = input_value
        if "temperature" in weather_data:
            # Scale input value based on temperature
            temp_factor = weather_data["temperature"] / 20  # Normalize around 20°C
            adjusted_input = input_value * temp_factor
        
        # Run the computation (will use cache if available)
        computation_data = self.computation_tool.run(adjusted_input, complexity=3)
        
        return {
            "weather": weather_data,
            "computation": computation_data,
            "aggregated_result": {
                "location": location,
                "input_value": input_value,
                "adjusted_input": adjusted_input,
                "weather_conditions": weather_data.get("conditions", "Unknown"),
                "final_result": computation_data["result"],
                "timestamp": time.time()
            }
        }
