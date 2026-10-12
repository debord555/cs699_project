import hashlib
import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "cmpid"}

JUNK_URL_PARTS = (
    "/video/", "/videos/", "/photo/", "/photos/", "/gallery/", "/slideshow/",
    "/web-stories/", "/webstories/", "/podcast/", "/horoscope/",
    "live-updates", "liveblog",
)


def normalize_url(url):
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), ""))


def url_hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def domain_of(url):
    return urlsplit(url).netloc.lower().removeprefix("www.")


def is_junk(url, title):
    url = url.lower()
    if any(part in url for part in JUNK_URL_PARTS):
        return True
    return re.search(r"\bLIVE\b", title) is not None


def clean_html(text):
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text or None


if __name__ == "__main__":
    assert normalize_url("https://WWW.Example.com/a/b?utm_source=x&id=5#top") == "https://www.example.com/a/b?id=5"
    assert normalize_url("https://www.ndtv.com/india-news/story-123#publisher=newsstand") == "https://www.ndtv.com/india-news/story-123"
    assert domain_of("https://www.thehindu.com/news/x") == "thehindu.com"
    assert is_junk("https://example.com/videos/abc", "Some title")
    assert is_junk("https://example.com/news/abc", "Delhi protest LIVE updates")
    assert not is_junk("https://example.com/news/abc", "Olive farmers protest")
    assert clean_html("<p>Hello &amp; <b>world</b></p>") == "Hello & world"
    print("All normalize checks passed")