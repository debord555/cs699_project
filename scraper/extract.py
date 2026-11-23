import hashlib

from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0

WIRE_AGENCIES = ["PTI", "IANS", "ANI", "UNI", "Reuters", "AFP"]

BYLINE_LINES = {
    "OUR BUREAU", "STAFF REPORTER", "A CORRESPONDENT", "OUR CORRESPONDENT",
    "SPECIAL CORRESPONDENT", "EXPRESS NEWS SERVICE", "HT CORRESPONDENT",
    "CORRESPONDENT", "STAFF CORRESPONDENT", "BUREAU",
}

NOT_PLACES = {
    "EXPLAINED", "WATCH", "OPINION", "EDITORIAL", "ANALYSIS", "EXCLUSIVE",
    "BREAKING", "UPDATE", "UPDATED", "REVIEW", "INTERVIEW", "ALSO READ", "READ",
    "NOTE", "BY", "BACKGROUND", "SOURCE", "PHOTO", "HIGHLIGHTS", "SUMMARY",
    "TOP HEADLINES", "CONTEXT",
}


def looks_like_place(text):
    words = text.split()
    if not 1 <= len(words) <= 3:
        return False
    if any(ch.isdigit() for ch in text):
        return False
    if text.upper() in NOT_PLACES:
        return False
    return all(word[0].isupper() for word in words)


def find_dateline(text):
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:4]:
        if line.upper() in BYLINE_LINES:
            continue

        has_agency = any(f"({agency})" in line[:60] for agency in WIRE_AGENCIES)
        if has_agency and "," in line:
            place = line.split(",")[0].strip()
            if looks_like_place(place):
                return place

        if ":" in line:
            place = line.split(":")[0].strip()
            if looks_like_place(place):
                return place

        if line.isupper() and looks_like_place(line):
            return line

    return None


def find_wire_agency(author, text):
    if author:
        for agency in WIRE_AGENCIES:
            if author.strip().upper() == agency.upper():
                return agency
    start_of_text = (text or "")[:300]
    for agency in WIRE_AGENCIES:
        if f"({agency})" in start_of_text:
            return agency
    return None


def detect_language(title, text):
    sample = f"{title or ''} {(text or '')[:1000]}".strip()
    if len(sample) < 20:
        return None
    try:
        return detect(sample)
    except Exception:
        return None


def content_hash(text):
    if not text or len(text) < 200:
        return None
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    assert find_dateline("PALAKKAD\nResidents of Pirayiri have alleged...") == "PALAKKAD"
    assert find_dateline("STAFF REPORTER\nGUWAHATI: Assam Pradesh Mahila Congress...") == "GUWAHATI"
    assert find_dateline("OUR BUREAU\nORANG/TANGLA: In a bid to...") == "ORANG/TANGLA"
    assert find_dateline("Imphal: At least 11 people were killed...") == "Imphal"
    assert find_dateline("Bhubaneswar, Oct 10 (PTI) The state government...") == "Bhubaneswar"
    assert find_dateline("NEW DELHI: The Supreme Court on Monday...") == "NEW DELHI"
    assert find_dateline("Explained: What the High Court said") is None
    assert find_dateline("THE CBI has arrested a DGCA official...") is None
    assert find_dateline("Ganpati Festival 2026:Central Railway will operate...") is None
    assert find_dateline("Delhi rail traffic update: Northern Railway has restored...") is None
    assert find_dateline("Assault on child: child rights panel registers case") is None
    assert find_dateline("By: Staff Writer\nThe state cabinet met...") is None
    assert find_dateline("CORRESPONDENT\nSHILLONG: The Wangala festival...") == "SHILLONG"
    assert find_dateline("Background: The market has grown...") is None
    assert find_wire_agency("PTI", "") == "PTI"
    assert find_wire_agency("HT News Desk", "Chandigarh, Oct 11 (PTI) The North...") == "PTI"
    assert find_wire_agency("Express News Service", "The CBI has arrested...") is None
    assert detect_language("Floods hit Assam", "Heavy rain has flooded several districts in Assam.") == "en"
    assert content_hash("short") is None
    assert content_hash("A " * 150) == content_hash("a  " * 150)
    print("All extract checks passed")
