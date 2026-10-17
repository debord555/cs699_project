

-- One row per news website
CREATE TABLE sources (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    domain        TEXT UNIQUE NOT NULL,          -- e.g. 'thehindu.com'
    language      TEXT NOT NULL DEFAULT 'en',
    region_scope  TEXT,                          -- 'national', 'Assam', 'North-East', ...
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

-- One row per RSS feed (a source can have many feeds)
CREATE TABLE feeds (
    id                    SERIAL PRIMARY KEY,
    source_id             INT NOT NULL REFERENCES sources(id),
    url                   TEXT UNIQUE NOT NULL,
    kind                  TEXT NOT NULL DEFAULT 'rss',   -- 'rss' or 'google_news'
    location_hint         TEXT,                          -- e.g. 'Kerala' for a Kerala feed
    category_hint         TEXT,                          -- e.g. 'Sports' for a sports feed
    poll_minutes          INT NOT NULL DEFAULT 30,
    etag                  TEXT,
    last_modified         TEXT,
    last_polled_at        TIMESTAMPTZ,
    consecutive_failures  INT NOT NULL DEFAULT 0,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE
);

-- One row per news article
CREATE TABLE articles (
    id              BIGSERIAL PRIMARY KEY,
    url             TEXT NOT NULL,
    url_hash        CHAR(64) UNIQUE NOT NULL,        -- sha256 of the cleaned URL, used to skip duplicates
    source_id       INT NOT NULL REFERENCES sources(id),
    feed_id         INT REFERENCES feeds(id),
    title           TEXT NOT NULL,
    summary         TEXT,                            -- short description from the feed
    body            TEXT,                            -- full text, for internal processing only
    dateline        TEXT,                            -- e.g. 'GUWAHATI'
    author          TEXT,
    image_url       TEXT,
    language        TEXT,
    published_at    TIMESTAMPTZ,                     -- stored in UTC
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_tags     TEXT[],                          -- the website's own tags/sections
    location_hint   TEXT,                            -- copied from the feed
    category_hint   TEXT,                            -- copied from the feed
    content_hash    CHAR(64),                        -- same text on many sites = same hash
    is_wire         BOOLEAN NOT NULL DEFAULT FALSE,  -- PTI / IANS / ANI copy
    status          TEXT NOT NULL DEFAULT 'new',     -- new -> ready -> (LLM step) llm_done / llm_failed
    fetch_attempts  INT NOT NULL DEFAULT 0,
    error           TEXT
);

-- One row per mentioned location
CREATE TABLE locations (
    id              BIGSERIAL PRIMARY KEY,
    location_name   TEXT,
    latitude        DOUBLE PRECISION CHECK (latitude BETWEEN -90 AND 90),
    longitude       DOUBLE PRECISION CHECK (longitude BETWEEN -180 AND 180)
);

-- For many to many mapping between articles and locations
CREATE TABLE article_location_map (
    article_id      BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    location_id     BIGINT NOT NULL REFERENCES locations(id),
    mention_order   INT,
    PRIMARY KEY (article_id, location_id)
);

CREATE INDEX idx_articles_status ON articles (status);
CREATE INDEX idx_articles_published_at ON articles (published_at);
CREATE INDEX idx_articles_content_hash ON articles (content_hash);
CREATE INDEX idx_alm_location ON article_location_map (location_id);

-- Case-insensitive name lookup: WHERE lower(location_name) = lower('Guwahati')
CREATE INDEX idx_locations_name_lower ON locations (lower(location_name));
-- Spatial lookup: bounding box (point(longitude, latitude) <@ box(...)) and nearest-first (ORDER BY ... <-> point(...))
CREATE INDEX idx_locations_point ON locations USING GIST (point(longitude, latitude));