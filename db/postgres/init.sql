CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS guest_users (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_settings (
  user_id UUID PRIMARY KEY REFERENCES guest_users(id) ON DELETE CASCADE,
  language TEXT NOT NULL DEFAULT 'en-US',
  theme TEXT NOT NULL DEFAULT 'system',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (language IN ('en-US', 'zh-CN')),
  CHECK (theme IN ('system', 'light', 'dark'))
);

CREATE TABLE IF NOT EXISTS stories (
  id UUID PRIMARY KEY,
  story_id UUID NOT NULL UNIQUE,
  user_id UUID NOT NULL REFERENCES guest_users(id) ON DELETE CASCADE,
  story_title TEXT NULL,
  user_input TEXT NOT NULL,
  gender_preference TEXT NOT NULL DEFAULT 'male',
  culture_language TEXT NOT NULL DEFAULT 'en-US',
  is_public BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (gender_preference IN ('male', 'female')),
  CHECK (culture_language IN ('en-US', 'zh-CN')),
  CHECK (status IN ('pending', 'generating', 'completed', 'failed', 'error'))
);

CREATE TABLE IF NOT EXISTS story_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES guest_users(id) ON DELETE CASCADE,
  story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  session_id UUID NOT NULL,
  scene_id TEXT NULL,
  episode_number INTEGER NULL,
  round_number INTEGER NULL,
  event_type TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (event_type IN ('user_input', 'ai_response', 'game_start', 'skip_scene', 'system_message'))
);

CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id);
CREATE INDEX IF NOT EXISTS idx_stories_is_public ON stories(is_public);
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_story_events_story_id ON story_events(story_id);
CREATE INDEX IF NOT EXISTS idx_story_events_user_id ON story_events(user_id);
CREATE INDEX IF NOT EXISTS idx_story_events_created_at ON story_events(created_at);
