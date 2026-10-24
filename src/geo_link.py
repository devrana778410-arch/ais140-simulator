# Universal Google Maps & WhatsApp Location Link Extractor
import urllib.parse
import re
import math
from typing import Optional, Tuple
from .rto_data import RTO_TABLE


def extract_coordinates(url_or_text: str) -> Optional[Tuple[float, float]]:
    """
    Extract (latitude, longitude) as floats from any Google Maps link,
    WhatsApp shared text, geo URI, or raw coordinate string.

    Supported Formats:
      1. https://maps.google.com/maps?q=21.86664%2C73.1830466&z=17&hl=en
      2. https://maps.google.com/?q=21.86664,73.1830466
      3. https://www.google.com/maps/search/?api=1&query=21.86664,73.1830466
      4. https://www.google.com/maps/@21.86664,73.1830466,17z
      5. geo:21.86664,73.1830466
      6. Text sharing: "Check my location: https://maps.google.com/maps?q=21.86664%2C73.1830466"
      7. Raw coordinate pair: "21.86664, 73.1830466"
    """
    if not url_or_text:
        return None

    # URL decode characters like %2C -> ','
    text = urllib.parse.unquote(url_or_text.strip())

    # 1. Query parameters: ?q=lat,lon or &q=lat,lon or query=lat,lon or &ll=lat,lon
    m = re.search(r"[?&](?:q|query|ll)=(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass

    # 2. Path format: /maps/@lat,lon,zoom
    m = re.search(r"@(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass

    # 3. geo URI: geo:lat,lon
    m = re.search(r"geo:(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            pass

    # 4. Fallback: Generic decimal coordinate pair (e.g. 21.86664, 73.1830466)
    m = re.search(r"\b(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})\b", text)
    if m:
        try:
            lat = float(m.group(1))
            lon = float(m.group(2))
            # Validate bounds
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return lat, lon
        except ValueError:
            pass

    return None


def find_nearest_rto(lat: float, lon: float) -> Tuple[str, str, float]:
    """
    Find the closest Gujarat / UT RTO to the given coordinates.
    Returns (rto_code, rto_name, distance_in_km).
    """
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    best_code = "GJ-01"
    best_dist = float("inf")

    for code, info in RTO_TABLE.items():
        dist = haversine(lat, lon, info["lat"], info["lon"])
        if dist < best_dist:
            best_dist = dist
            best_code = code

    return best_code, RTO_TABLE[best_code]["name"], best_dist
