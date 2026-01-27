"""GESTIMA - Miscellaneous Router (Joke, Weather)"""

import logging
import httpx
import feedparser
import random
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# RSS FEED SOURCES
# ============================================================================

RSS_SOURCES = [
    "https://www.osel.cz/rss/rss.php",
    "https://vtm.zive.cz/rss.ashx",
    "https://www.irozhlas.cz/rss/irozhlas/section/veda-technologie",
    "http://21stoleti.cz/feed/rss/"
]


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class FactItem(BaseModel):
    """Single fact item"""
    title: str
    text: str
    url: str

class FactResponse(BaseModel):
    """Response pro facts - contains 2 articles"""
    facts: List[FactItem]


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
@limiter.limit("10/minute")
async def get_fact(request: Request) -> FactResponse:
    """
    Fetch 2 random articles from Czech RSS feeds.
    Rotates between OSEL.cz, VTM.cz, iROZHLAS, and 21stoleti.cz.
    Returns truncated text (3-4 lines) + link to full article.
    """
    facts = []

    try:
        # Randomly select a source
        source_url = random.choice(RSS_SOURCES)

        # Fetch RSS feed
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(source_url)
            response.raise_for_status()
            feed_content = response.text

        # Parse RSS feed
        feed = feedparser.parse(feed_content)

        if not feed.entries:
            raise ValueError("No entries in feed")

        # Get 2 random articles from the feed
        available_entries = feed.entries[:20]  # Use first 20 entries (most recent)
        selected_entries = random.sample(available_entries, min(2, len(available_entries)))

        for entry in selected_entries:
            title = entry.get("title", "Bez názvu")

            # Get description/summary
            text = entry.get("description", entry.get("summary", ""))

            # Strip HTML tags if present
            import re
            text = re.sub(r'<[^>]+>', '', text)

            # Truncate to ~150 chars (fit 2 articles)
            max_length = 150
            if len(text) > max_length:
                text = text[:max_length].rsplit(' ', 1)[0] + "..."

            url = entry.get("link", "")

            facts.append({
                "title": title,
                "text": text,
                "url": url
            })

        # If we got less than 2, pad with fallback
        while len(facts) < 2:
            facts.append({
                "title": "",
                "text": "Zajímavost se nepodařilo načíst.",
                "url": ""
            })

        return {"facts": facts}

    except httpx.TimeoutException:
        logger.warning("RSS feed timeout")
        return {
            "facts": [
                {"title": "", "text": "Zajímavost se načítá příliš dlouho...", "url": ""},
                {"title": "", "text": "Zajímavost se načítá příliš dlouho...", "url": ""}
            ]
        }
    except Exception as e:
        logger.error(f"RSS feed error: {e}", exc_info=True)
        return {
            "facts": [
                {"title": "", "text": "Zajímavost se nepodařilo načíst.", "url": ""},
                {"title": "", "text": "Zajímavost se nepodařilo načíst.", "url": ""}
            ]
        }


# ============================================================================
# WEATHER API
# ============================================================================

@router.get("/weather", response_model=WeatherResponse)
@limiter.limit("10/minute")
async def get_weather(request: Request) -> WeatherResponse:
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
