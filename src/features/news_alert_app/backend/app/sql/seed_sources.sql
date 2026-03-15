-- Seed default news sources. Safe to run repeatedly (ON CONFLICT = no-op).

INSERT INTO sources (id, name, slug, source_type, base_url, rss_url, api_url, trust_tier, is_active, polling_interval_seconds, notes)
VALUES
  (
    'a1b2c3d4-0001-4000-8000-000000000001',
    'Reuters World News',
    'reuters-world',
    'RSS',
    'https://www.reuters.com',
    'https://www.reutersagency.com/feed/?best-topics=political-general',
    NULL,
    'HIGH',
    TRUE,
    300,
    'Reuters world/political RSS feed'
  ),
  (
    'a1b2c3d4-0002-4000-8000-000000000002',
    'Al Jazeera',
    'aljazeera',
    'RSS',
    'https://www.aljazeera.com',
    'https://www.aljazeera.com/xml/rss/all.xml',
    NULL,
    'HIGH',
    TRUE,
    300,
    'Al Jazeera full RSS feed'
  ),
  (
    'a1b2c3d4-0003-4000-8000-000000000003',
    'BBC News World',
    'bbc-world',
    'RSS',
    'https://www.bbc.com/news',
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    NULL,
    'VERIFIED',
    TRUE,
    300,
    'BBC World News RSS'
  ),
  (
    'a1b2c3d4-0004-4000-8000-000000000004',
    'NewsAPI Everything',
    'newsapi-everything',
    'API',
    'https://newsapi.org',
    NULL,
    'https://newsapi.org/v2/everything',
    'MEDIUM',
    TRUE,
    600,
    'NewsAPI everything endpoint — requires NEWSAPI_KEY'
  )
ON CONFLICT (name) DO NOTHING;
