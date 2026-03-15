-- Create enum types used by sources table (safe to run multiple times)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type_enum') THEN
        CREATE TYPE source_type_enum AS ENUM (
            'RSS',
            'API',
            'WEBSITE',
            'SOCIAL',
            'GOVERNMENT',
            'OTHER'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trust_tier_enum') THEN
        CREATE TYPE trust_tier_enum AS ENUM (
            'LOW',
            'MEDIUM',
            'HIGH',
            'VERIFIED'
        );
    END IF;
END $$;

-- Create sources table
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    source_type source_type_enum NOT NULL,
    base_url TEXT NULL,
    rss_url TEXT NULL,
    api_url TEXT NULL,
    trust_tier trust_tier_enum NOT NULL DEFAULT 'MEDIUM',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    polling_interval_seconds INTEGER NOT NULL DEFAULT 300,
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
