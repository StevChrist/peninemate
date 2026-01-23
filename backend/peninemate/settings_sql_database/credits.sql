CREATE TABLE IF NOT EXISTS credits (
  id SERIAL PRIMARY KEY,
  movie_tmdb_id INTEGER NOT NULL,
  person_tmdb_person_id INTEGER NOT NULL,
  credit_type TEXT NOT NULL,     -- 'cast' or 'crew'

  department TEXT,               -- crew
  job TEXT,                      -- crew
  character_name TEXT,           -- cast
  cast_order INTEGER,            -- cast

  FOREIGN KEY (movie_tmdb_id) REFERENCES movies(tmdb_id) ON DELETE CASCADE,
  FOREIGN KEY (person_tmdb_person_id) REFERENCES people(tmdb_person_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_credits_movie ON credits(movie_tmdb_id);
CREATE INDEX IF NOT EXISTS idx_credits_person ON credits(person_tmdb_person_id);
