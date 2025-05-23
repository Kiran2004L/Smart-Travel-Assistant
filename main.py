#!/usr/bin/env python3
"""
Smart Travel Assistant v3
Displays current weather, tourist attractions, nearby hotels, images, distances, and map links.
"""

import sys
import requests
from math import radians, sin, cos, sqrt, atan2
from geopy.geocoders import Nominatim
import webbrowser  # To open URLs in the web browser
from urllib.parse import quote_plus # To safely encode city names for URLs

# ====== CONFIGURATION ======
WEATHER_API_KEY = "1e17b5f27764134c0427f138aac5e0ae"
GEOAPIFY_API_KEY = "ef4fbad565e647c9a0a2d0a491cf460b"
UNSPLASH_ACCESS_KEY = "k5IXA4EaIZhKXUO4r0Y8QU1zzhoZvdbQb3bmFkV2fOw"

# Sanity check for placeholders
if any(key.startswith("YOUR_") for key in (WEATHER_API_KEY, GEOAPIFY_API_KEY, UNSPLASH_ACCESS_KEY)):
    print("❌ ERROR: Please replace all placeholder API keys with your own.")
    sys.exit(1)

# Initialize geocoder with a custom User-Agent
geolocator = Nominatim(user_agent="smart_travel_assistant/1.0")

def get_coordinates(city: str):
    """Convert a city name into (latitude, longitude)."""
    try:
        loc = geolocator.geocode(city, timeout=10)
    except Exception as e:
        print(f"❌ Geocoding error: {e}")
        sys.exit(1)
    if not loc:
        print("❌ City not found. Please check the spelling and try again.")
        sys.exit(1)
    return loc.latitude, loc.longitude

def fetch_weather(city: str):
    """Fetch current weather for a city by name."""
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
    )
    try:
        r = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"❌ Network error while fetching weather: {e}")
        sys.exit(1)
    if r.status_code == 401:
        print("❌ Weather API error 401: Invalid or inactive API key.")
        sys.exit(1)
    if r.status_code != 200:
        print(f"❌ Weather API error {r.status_code}: {r.text}")
        sys.exit(1)
    data = r.json()
    return {
        "temp": data["main"]["temp"],
        "desc": data["weather"][0]["description"].capitalize(),
        "humidity": data["main"]["humidity"]
    }

def haversine(lat1, lon1, lat2, lon2):
    """Return distance in kilometers between two lat/lon pairs."""
    R = 6371  # Earth radius in km
    φ1, φ2 = radians(lat1), radians(lat2)
    Δφ = radians(lat2 - lat1)
    Δλ = radians(lon2 - lon1)
    a = sin(Δφ/2)**2 + cos(φ1)*cos(φ2)*sin(Δλ/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def fetch_places(lat, lon, category, limit=5, radius=5000):
    """Fetch nearby places from Geoapify for a given category."""
    url = (
        "https://api.geoapify.com/v2/places"
        f"?categories={category}"
        f"&filter=circle:{lon},{lat},{radius}"
        f"&limit={limit}"
        f"&apiKey={GEOAPIFY_API_KEY}"
    )
    try:
        r = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"❌ Network error while fetching {category}: {e}")
        sys.exit(1)
    if r.status_code == 401:
        print(f"❌ Places API error 401 for {category}: Invalid API key.")
        sys.exit(1)
    if r.status_code != 200:
        print(f"❌ Places API error {r.status_code}: {r.text}")
        sys.exit(1)
    return r.json().get("features", [])

def fetch_image(place_name: str):
    """Try Wikipedia first, then Unsplash fallback, to get an image URL."""
    # 1. Wikipedia thumbnail
    try:
        wiki_res = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 600,
                "titles": place_name
            },
            timeout=5
        ).json()
        pages = wiki_res["query"]["pages"]
        for p in pages.values():
            thumb = p.get("thumbnail", {}).get("source")
            if thumb:
                return thumb
    except Exception:
        pass

    # 2. Unsplash fallback
    try:
        unsplash_res = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": place_name,
                "client_id": UNSPLASH_ACCESS_KEY,
                "per_page": 1
            },
            timeout=5
        ).json()
        results = unsplash_res.get("results", [])
        if results:
            return results[0]["urls"]["regular"]
    except Exception:
        pass

    return "❌ No image available"

def main():
    city = input("Enter your city name: ").strip()
    if not city:
        print("❌ No city entered. Exiting.")
        return

    lat, lon = get_coordinates(city) # Script exits here if city not found

    # --- New feature: Open browser with general city info/attractions ---
    try:
        city_for_url = quote_plus(city) # URL-encode the city name (e.g., "New York" -> "New+York")

        # Option 1: Open Google Maps centered on the city (often shows points of interest)
        overview_url = f"https://www.google.com/maps/place/{city_for_url}"

        # Option 2: More specific Google search for tourist attractions (alternative)
        # overview_url = f"https://www.google.com/search?q=tourist+attractions+in+{city_for_url}"

        # Option 3: Google Maps search for "tourist attractions in [city]" (alternative)
        # overview_url = f"https://www.google.com/maps/search/tourist+attractions+in+{city_for_url}"

        print(f"\nℹ️  Opening Google Maps for '{city.capitalize()}' in your browser for an overview and recommendations...")
        webbrowser.open_new_tab(overview_url)
    except Exception as e:
        # This catches potential errors with opening the browser
        print(f"⚠️  Could not automatically open a browser tab for {city.capitalize()}: {e}")
    # --- End of new feature ---

    weather = fetch_weather(city)

    # Print weather
    print(f"\n📍 City: {city.capitalize()}") # Used capitalize() for consistent display
    print(f"🌦️ Weather: {weather['desc']}, {weather['temp']}°C")
    print(f"💧 Humidity: {weather['humidity']}%\n")

    # Tourist sights
    print("🗺️ Top Tourist Attractions Nearby:")
    # Ensure you have the corrected categories from our previous discussion here:
    # e.g., "tourism.sights,tourism.attraction,leisure.park,tourism.sights.castle"
    sights_categories = "tourism.sights,tourism.attraction,leisure.park,tourism.sights.castle" # Use your corrected categories
    sights = fetch_places(lat, lon, sights_categories, limit=10, radius=40000)

    if not sights:
        print(f"No tourist sights found for '{city.capitalize()}' within 40 km using the script's sources.\n")
    else:
        for feat in sights:
            p = feat["properties"]
            name = p.get("name", "Unnamed Place")
            addr = p.get("formatted", "No address available")
            plat, plon = feat["geometry"]["coordinates"][1], feat["geometry"]["coordinates"][0]
            dist = haversine(lat, lon, plat, plon)
            img_url = fetch_image(name)
            # Corrected maps link from previous discussion
            maps_link = f"https://www.google.com/maps/?q={plat},{plon}"
            print(f"🔹 {name} ({dist:.1f} km away)")
            print(f"     Address: {addr}")
            print(f"     Image: {img_url}")
            print(f"     Map: {maps_link}\n")

    # Hotels / Accommodation
    print("🏨 Nearby Hotels:")
    hotels = fetch_places(lat, lon, "accommodation.hotel", limit=5, radius=5000)
    if not hotels:
        print(f"No hotels found for '{city.capitalize()}' within 5 km using the script's sources.\n")
    else:
        for feat in hotels:
            p = feat["properties"]
            name = p.get("name", "Unnamed Hotel")
            addr = p.get("formatted", "No address available")
            hlat, hlon = feat["geometry"]["coordinates"][1], feat["geometry"]["coordinates"][0]
            dist = haversine(lat, lon, hlat, hlon)
            img_url = fetch_image(name)
            # Corrected maps link from previous discussion
            maps_link = f"https://www.google.com/maps/?q={hlat},{hlon}"
            print(f"🔹 {name} ({dist:.1f} km away)")
            print(f"     Address: {addr}")
            print(f"     Image: {img_url}")
            print(f"     Map: {maps_link}\n")

if __name__ == "__main__":
    main()
