# Supabase Setup Instructions

## 1. Create Project
1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Wait for the project to be provisioned.

## 2. Run SQL Schema
1. Open **SQL Editor** in your Supabase project.
2. Copy the contents of `setup.sql` and run it.

## 3. Create Storage Bucket
1. Go to **Storage** in the Supabase Dashboard.
2. Click **New bucket**.
3. Name: `viral-videos`
4. Set **Public bucket** to ON (so video URLs work for playback).
5. Create the bucket.

## 4. Get Credentials
1. Go to **Settings** → **API**.
2. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** key (not anon) → `SUPABASE_SERVICE_KEY`

## 5. Environment Variables
Create `backend/.env`:

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-...
NEUROAPI_BASE_URL=https://api.neuroapi.com/v1
```

## 6. Seed Data (optional)
```sql
INSERT INTO topics (keyword, description) VALUES
  ('Tech', 'Technology and gadgets'),
  ('Humor', 'Funny viral content');

INSERT INTO sources (platform, url, status) VALUES
  ('shorts', 'https://youtube.com/@test', 'active');
```
