import os
import requests
import streamlit as st

def get_live_weather(city_name: str) -> dict:
    """Fetches real-time temperature, humidity, and weather conditions from OpenWeatherMap."""
    weather_key = None
    try:
        if "OPENWEATHER_API_KEY" in st.secrets:
            weather_key = st.secrets["OPENWEATHER_API_KEY"]
    except Exception:
        pass
    
    if not weather_key:
        weather_key = os.getenv("OPENWEATHER_API_KEY")

    if not weather_key:
        return {"error": "Weather API key missing."}

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={weather_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["description"],
                "city": data["name"],
                "raw_text": f"Location: {data['name']}, Temp: {data['main']['temp']}°C, Humidity: {data['main']['humidity']}%, Sky: {data['weather'][0]['description']}."
            }
        else:
            return {"error": f"City '{city_name}' not found."}
    except Exception:
        return {"error": "Weather lookup failed (Timeout)."}
