CREATE TABLE IF NOT EXISTS movies (
  id SERIAL PRIMARY KEY,
  tmdb_id INTEGER UNIQUE NOT NULL,
  title TEXT NOT NULL,
  original_title TEXT,
  release_date DATE,
  year INTEGER,
  overview TEXT,
  genres_json JSONB,
  popularity DOUBLE PRECISION,
  vote_average DOUBLE PRECISION,
  vote_count INTEGER,
  poster_path TEXT,
  backdrop_path TEXT,
  fetched_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);
CREATE INDEX IF NOT EXISTS idx_movies_popularity ON movies(popularity);

CREATE TABLE IF NOT EXISTS people (
  id SERIAL PRIMARY KEY,
  tmdb_person_id INTEGER UNIQUE NOT NULL,
  name TEXT NOT NULL,
  gender INTEGER,
  known_for_department TEXT,
  profile_path TEXT,
  fetched_at TIMESTAMP DEFAULT NOW()
);