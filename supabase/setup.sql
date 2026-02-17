-- Trend Watching Web Service - Supabase Schema
-- Run this in Supabase SQL Editor

-- Enum for platform
CREATE TYPE platform_enum AS ENUM ('tiktok', 'reels', 'shorts');

-- Enum for source status
CREATE TYPE source_status_enum AS ENUM ('active', 'inactive');

-- Sources table
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform platform_enum NOT NULL,
    url TEXT NOT NULL,
    status source_status_enum NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Topics table
CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Videos table
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    ai_summary TEXT,
    virality_score INT CHECK (virality_score >= 1 AND virality_score <= 10) DEFAULT 5,
    is_viral BOOLEAN NOT NULL DEFAULT FALSE,
    storage_path TEXT,
    quality_decision_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, external_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_videos_is_viral ON videos(is_viral);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_source_id ON videos(source_id);

-- Enable RLS (Row Level Security) - optional, adjust policies as needed
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access (used with service key)
-- If using anon key, you'll need different policies
CREATE POLICY "Service role full access on sources" ON sources
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on topics" ON topics
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on videos" ON videos
    FOR ALL USING (true) WITH CHECK (true);

-- Create Storage bucket for viral videos (run in Supabase Dashboard or via API)
-- Bucket: viral-videos
-- Public: true (for video playback)
