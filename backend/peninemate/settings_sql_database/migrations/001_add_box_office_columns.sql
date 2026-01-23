-- migrations/001_add_box_office_columns.sql (PostgreSQL Version)

-- Add box office columns (PostgreSQL syntax)
ALTER TABLE movies 
  ADD COLUMN IF NOT EXISTS box_office_worldwide BIGINT,
  ADD COLUMN IF NOT EXISTS box_office_domestic BIGINT,
  ADD COLUMN IF NOT EXISTS box_office_foreign BIGINT;

-- Add data source tracking
ALTER TABLE movies 
  ADD COLUMN IF NOT EXISTS data_source TEXT DEFAULT 'tmdb';

-- Add genres from CSV (separate from genres_json)
ALTER TABLE movies 
  ADD COLUMN IF NOT EXISTS genres_csv TEXT;

-- Use existing 'popularity' column (no need to add popularity_score)

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_movies_title_year ON movies(title, year);
CREATE INDEX IF NOT EXISTS idx_movies_data_source ON movies(data_source);
CREATE INDEX IF NOT EXISTS idx_movies_box_office ON movies(box_office_worldwide);

-- Update existing data
UPDATE movies SET data_source = 'tmdb' WHERE data_source IS NULL;