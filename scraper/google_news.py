from urllib.parse import quote_plus

from googlenewsdecoder import gnewsdecoder


def search_url(place):
    query = quote_plus(f'"{place}"')
    return f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def real_link(google_link):
    try:
        result = gnewsdecoder(google_link, interval=1)
    except Exception:
        return None
    if result.get("status"):
        return result["decoded_url"]
    return None
