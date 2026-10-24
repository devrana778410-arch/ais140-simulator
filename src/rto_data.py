# Official RTO lookup table for Gujarat and Union Territories (Daman, Diu, Silvassa)
# Verified against official Gujarat Motor Vehicle Department (GVD) listings.
# Format: RTO_CODE -> {"name": str, "lat": float, "lon": float}

RTO_TABLE = {
    # --- Gujarat (GJ-01 to GJ-38) ---
    "GJ-01": {"name": "Ahmedabad (West - Subhash Bridge)", "lat": 23.0617, "lon": 72.5802},
    "GJ-02": {"name": "Mehsana",                          "lat": 23.5880, "lon": 72.3693},
    "GJ-03": {"name": "Rajkot",                           "lat": 22.3039, "lon": 70.8022},
    "GJ-04": {"name": "Bhavnagar",                        "lat": 21.7645, "lon": 72.1519},
    "GJ-05": {"name": "Surat (City)",                     "lat": 21.1702, "lon": 72.8311},
    "GJ-06": {"name": "Vadodara (City)",                  "lat": 22.3072, "lon": 73.1812},
    "GJ-07": {"name": "Nadiad (Kheda)",                   "lat": 22.6916, "lon": 72.8634},
    "GJ-08": {"name": "Palanpur (Banaskantha)",           "lat": 24.1718, "lon": 72.4346},
    "GJ-09": {"name": "Himmatnagar (Sabarkantha)",         "lat": 23.5979, "lon": 72.9698},
    "GJ-10": {"name": "Jamnagar",                         "lat": 22.4707, "lon": 70.0577},
    "GJ-11": {"name": "Junagadh",                         "lat": 21.5222, "lon": 70.4579},
    "GJ-12": {"name": "Bhuj (Kutch)",                     "lat": 23.2420, "lon": 69.6669},
    "GJ-13": {"name": "Surendranagar",                    "lat": 22.7272, "lon": 71.6487},
    "GJ-14": {"name": "Amreli",                           "lat": 21.6040, "lon": 71.2218},
    "GJ-15": {"name": "Valsad",                           "lat": 20.6116, "lon": 72.9289},
    "GJ-16": {"name": "Bharuch",                          "lat": 21.7051, "lon": 72.9959},
    "GJ-17": {"name": "Godhra (Panchmahal)",              "lat": 22.7758, "lon": 73.6149},
    "GJ-18": {"name": "Gandhinagar",                      "lat": 23.2156, "lon": 72.6369},
    "GJ-19": {"name": "Bardoli (Surat East)",             "lat": 21.1215, "lon": 73.1118},
    "GJ-20": {"name": "Dahod",                            "lat": 22.8347, "lon": 74.2546},
    "GJ-21": {"name": "Navsari",                          "lat": 20.9467, "lon": 72.9520},
    "GJ-22": {"name": "Rajpipla (Narmada)",               "lat": 21.8703, "lon": 73.5027},
    "GJ-23": {"name": "Anand",                            "lat": 22.5645, "lon": 72.9289},
    "GJ-24": {"name": "Patan",                            "lat": 23.8494, "lon": 72.1266},
    "GJ-25": {"name": "Porbandar",                        "lat": 21.6417, "lon": 69.6293},
    "GJ-26": {"name": "Vyara (Tapi)",                     "lat": 21.1121, "lon": 73.3934},
    "GJ-27": {"name": "Ahmedabad (East - Vastral)",       "lat": 22.9986, "lon": 72.6468},
    "GJ-28": {"name": "Surat (Rural - Pal)",              "lat": 21.1959, "lon": 72.7753},
    "GJ-29": {"name": "Vadodara (Rural)",                 "lat": 22.3150, "lon": 73.2000},
    "GJ-30": {"name": "Ahwa (Dang)",                      "lat": 20.7584, "lon": 73.6874},
    "GJ-31": {"name": "Modasa (Aravalli)",                "lat": 23.4616, "lon": 73.3005},
    "GJ-32": {"name": "Veraval (Gir Somnath)",            "lat": 20.9077, "lon": 70.3676},
    "GJ-33": {"name": "Botad",                            "lat": 22.1698, "lon": 71.6659},
    "GJ-34": {"name": "Chhota Udepur",                    "lat": 22.3041, "lon": 74.0147},
    "GJ-35": {"name": "Lunawada (Mahisagar)",             "lat": 23.1325, "lon": 73.6186},
    "GJ-36": {"name": "Morbi",                            "lat": 22.8173, "lon": 70.8373},
    "GJ-37": {"name": "Khambhalia (Devbhumi Dwarka)",     "lat": 22.2056, "lon": 69.6583},
    "GJ-38": {"name": "Bavla (Ahmedabad Rural)",          "lat": 22.8344, "lon": 72.3619},

    # --- Union Territories ---
    "DD-01": {"name": "Daman",                            "lat": 20.3974, "lon": 72.8328},
    "DD-02": {"name": "Diu",                              "lat": 20.7144, "lon": 70.9874},
    "DN-01": {"name": "Silvassa (Dadra & Nagar Haveli)",   "lat": 20.2733, "lon": 72.9986},
    "DN-09": {"name": "Dadra & Nagar Haveli (Silvassa)",  "lat": 20.2733, "lon": 72.9986},
}

# Sorted list of RTO codes for the dropdown
RTO_CODES = sorted(RTO_TABLE.keys())


def get_rto_coords(code: str) -> tuple[float, float]:
    """Return (lat, lon) for a given RTO code. Falls back to Ahmedabad."""
    entry = RTO_TABLE.get(code, RTO_TABLE["GJ-01"])
    return entry["lat"], entry["lon"]


def get_rto_display_list() -> list[str]:
    """Return list of 'GJ-01 – Ahmedabad...' style labels for the dropdown."""
    return [f"{code} – {RTO_TABLE[code]['name']}" for code in RTO_CODES]


def code_from_display(display: str) -> str:
    """Extract RTO code from a display string like 'GJ-01 – Ahmedabad...'."""
    return display.split(" – ")[0].strip()


def search_rto(query: str) -> list[str]:
    """
    Search RTO list matching code (e.g. '05', 'GJ-05', 'GJ05')
    or district name (e.g. 'Surat', 'Bharuch', 'Ahmedabad').
    Ranks prefix matches (e.g. 'bh' -> 'Bharuch', 'Bhavnagar', 'Bhuj') at the top!
    """
    q = query.strip().lower()
    if not q:
        # Default recommendations: major industrial/transport hubs
        priority_codes = ["GJ-16", "GJ-01", "GJ-05", "GJ-06", "GJ-03", "GJ-12", "GJ-18"]
        items = [f"{c} – {RTO_TABLE[c]['name']}" for c in priority_codes if c in RTO_TABLE]
        items += [f"{c} – {d['name']}" for c, d in sorted(RTO_TABLE.items()) if c not in priority_codes]
        return items

    city_prefix = []
    word_prefix = []
    code_match = []
    contains_match = []

    for code, info in sorted(RTO_TABLE.items()):
        name = info["name"]
        nl = name.lower()
        cl = code.lower()
        item = f"{code} – {name}"

        # Words in city name
        words = nl.replace("(", " ").replace(")", " ").replace("-", " ").split()
        if words and words[0].startswith(q):
            # E.g. 'Bharuch', 'Bhavnagar', 'Bhuj' start with 'bh'
            city_prefix.append(item)
        elif any(w.startswith(q) for w in words[1:]):
            word_prefix.append(item)
        elif cl.startswith(q) or cl.replace("-", "").startswith(q) or cl.split("-")[-1].startswith(q):
            code_match.append(item)
        elif q in nl or q in cl:
            contains_match.append(item)

    ranked = city_prefix + word_prefix + code_match + contains_match
    seen = set()
    dedup = []
    for x in ranked:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup


def resolve_rto(query: str) -> tuple[str, float, float]:
    """
    Smart resolver: takes user input (full display label, RTO code, or city name)
    and returns (code, lat, lon). Falls back to Ahmedabad if no match.
    """
    q = query.strip()
    if not q:
        return "GJ-01", RTO_TABLE["GJ-01"]["lat"], RTO_TABLE["GJ-01"]["lon"]

    code = code_from_display(q).upper()
    if code in RTO_TABLE:
        return code, RTO_TABLE[code]["lat"], RTO_TABLE[code]["lon"]

    matches = search_rto(q)
    if matches:
        first_code = code_from_display(matches[0])
        return first_code, RTO_TABLE[first_code]["lat"], RTO_TABLE[first_code]["lon"]

    return "GJ-01", RTO_TABLE["GJ-01"]["lat"], RTO_TABLE["GJ-01"]["lon"]
