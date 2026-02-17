-- Add quality_decision_reason column for stable quality gate (run if videos table already exists)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS quality_decision_reason TEXT;
