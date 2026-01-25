"""GESTIMA - Miscellaneous Router (Joke, Weather)"""

import logging
import httpx
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class FactResponse(BaseModel):
    """Response pro Wikipedia fact"""
    title: str
    text: str
    url: str


class WeatherPeriod(BaseModel):
    """Počasí pro jedno období"""
    temp: str
    icon: str


class WeatherResponse(BaseModel):
    """Response pro počasí"""
    location: str
    morning: WeatherPeriod
    afternoon: WeatherPeriod
    evening: WeatherPeriod


# ============================================================================
# JOKE API
# ============================================================================

@router.get("/fact", response_model=FactResponse)
async def get_fact() -> FactResponse:
    """
    Fetch random article from Czech Wikipedia.
    Returns truncated text (3-4 lines) + link to full article.
    """
    try:
        headers = {"User-Agent": "GESTIMA/1.0 (Educational App; Czech Republic)"}
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(
                "https://cs.wikipedia.org/api/rest_v1/page/random/summary",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # Extract title, extract, and URL
            title = data.get("title", "")
            extract = data.get("extract", "Zajímavost se nepodařilo načíst.")
            url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

            # Truncate extract to ~200 chars (3-4 lines)
            max_length = 200
            if len(extract) > max_length:
                extract = extract[:max_length].rsplit(' ', 1)[0] + "..."

            return {
                "title": title,
                "text": extract,
                "url": url
            }

    except httpx.TimeoutException:
        logger.warning("Wiki API timeout")
        return {"title": "", "text": "Zajímavost se načítá příliš dlouho...", "url": ""}
    except Exception as e:
        logger.error(f"Wiki API error: {e}", exc_info=True)
        return {"title": "", "text": "Zajímavost se nepodařilo načíst.", "url": ""}


# ============================================================================
# WEATHER API
# ============================================================================

@router.get("/weather", response_model=WeatherResponse)
async def get_weather() -> WeatherResponse:
    """
    Fetch weather for Ústí nad Orlicí from Open-Meteo API.
    Returns morning (6:00), afternoon (12:00), evening (18:00) forecast.
    """
    try:
        # Ústí nad Orlicí coordinates
        params = {
            "latitude": 49.97,
            "longitude": 16.39,
            "hourly": "temperature_2m,weathercode",
            "timezone": "auto",
            "forecast_days": 1
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weathercode", [])

            # Find indices for 6:00, 12:00, 18:00
            def find_hour_index(target_hour: int):
                for i, time_str in enumerate(times):
                    hour = int(time_str.split("T")[1].split(":")[0])
                    if hour == target_hour:
                        return i
                return None

            morning_idx = find_hour_index(6)
            afternoon_idx = find_hour_index(12)
            evening_idx = find_hour_index(18)

            # Weather code to emoji mapping (Open-Meteo WMO codes)
            def get_weather_emoji(code):
                if code is None:
                    return "🌤️"
                code = int(code)
                if code == 0: return "☀️"  # Clear
                if code in [1, 2]: return "⛅"  # Partly cloudy
                if code == 3: return "☁️"  # Overcast
                if code in [45, 48]: return "🌁"  # Fog
                if code in [51, 53, 55, 56, 57]: return "🌧️"  # Drizzle
                if code in [61, 63, 65, 66, 67]: return "🌧️"  # Rain
                if code in [71, 73, 75, 77]: return "🌨️"  # Snow
                if code in [80, 81, 82]: return "🌧️"  # Rain showers
                if code in [85, 86]: return "🌨️"  # Snow showers
                if code in [95, 96, 99]: return "⛈️"  # Thunderstorm
                return "🌤️"

            def format_period(idx):
                if idx is None or idx >= len(temps):
                    return {"temp": "?", "icon": "🌤️"}
                temp = round(temps[idx])
                code = codes[idx] if idx < len(codes) else None
                emoji = get_weather_emoji(code)
                return {"temp": f"{temp}°C", "icon": emoji}

            return {
                "location": "Ústí nad Orlicí",
                "morning": format_period(morning_idx),
                "afternoon": format_period(afternoon_idx),
                "evening": format_period(evening_idx)
            }

    except httpx.TimeoutException:
        logger.warning("Weather API timeout")
        return {
            "location": "Ústí nad Orlicí",
            "morning": {"temp": "?", "icon": "🌤️"},
            "afternoon": {"temp": "?", "icon": "🌤️"},
            "evening": {"temp": "?", "icon": "🌤️"}
        }
    except Exception as e:
        logger.error(f"Weather API error: {e}", exc_info=True)
        return {
            "location": "Ústí nad Orlicí",
            "morning": {"temp": "?", "icon": "🌤️"},
            "afternoon": {"temp": "?", "icon": "🌤️"},
            "evening": {"temp": "?", "icon": "🌤️"}
        }
