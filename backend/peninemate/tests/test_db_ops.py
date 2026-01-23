# tests/test_db_ops.py
import pytest
from unittest.mock import patch, MagicMock

from infrastructure.db_ops import ingest_one_movie
from core_logic.qa_db import (
    search_movies, 
    get_movie_cast_by_tmdb_id, 
    get_movie_crew_by_tmdb_id
)
from core_logic.qa_service import answer_director_question


@pytest.fixture
def mock_tmdb_movie_data():
    """Mock TMDb The Matrix lengkap."""
    return {
        "search_movie": MagicMock(return_value={
            "results": [{
                "id": 603,
                "title": "The Matrix",
                "release_date": "1999-03-31"
            }]
        }),
        "get_movie_details": MagicMock(return_value={
            "id": 603,
            "title": "The Matrix",
            "release_date": "1999-03-31",
            "overview": "A computer hacker...",
            "popularity": 123.45
        }),
        "get_movie_credits": MagicMock(return_value={
            "cast": [
                {"id": 6384, "name": "Keanu Reeves", "character": "Neo", "order": 1},
                {"id": 6393, "name": "Laurence Fishburne", "character": "Morpheus", "order": 2},
            ],
            "crew": [
                {"id": 6392, "name": "Lana Wachowski", "job": "Director"},
                {"id": 6391, "name": "Lilly Wachowski", "job": "Director"},
            ]
        }),
    }


def test_ingest_movie_cast(mock_tmdb_movie_data):
    """Step 1: Test cast ingest."""
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        tmdb_id = ingest_one_movie("The Matrix", year=1999, top_cast=2)
        assert tmdb_id == 603

        candidates = search_movies("Matrix")
        assert len(candidates) >= 1

        cast = get_movie_cast_by_tmdb_id(603, limit=2)
        assert len(cast) == 2
        assert cast[0][0] == "Keanu Reeves"


def test_ingest_movie_director(mock_tmdb_movie_data):
    """Step 1: Test Director ingest."""
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        ingest_one_movie("The Matrix", year=1999)

        directors = get_movie_crew_by_tmdb_id(603, job_filter="Director")
        assert len(directors) == 2
        assert directors[0]["name"] == "Lana Wachowski"


def test_get_movie_crew_filter(mock_tmdb_movie_data):
    """Step 2: Test crew query filter."""
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        ingest_one_movie("The Matrix", year=1999)
        
        directors = get_movie_crew_by_tmdb_id(603, job_filter="Director")
        assert len(directors) == 2
        
        all_crew = get_movie_crew_by_tmdb_id(603, job_filter=None)
        assert len(all_crew) == 2


def test_ingest_not_found():
    """Edge case: TMDb kosong."""
    with patch('peninemate.tmdb_client.search_movie', 
               return_value={"results": []}):
        result = ingest_one_movie("Film Fiktif")
        assert result is None


def test_answer_director_question(mock_tmdb_movie_data):
    """Step 3: End-to-end director wrapper."""
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        result = answer_director_question("The Matrix", year=1999, top_directors=2)
        
        # Intent & found
        assert result["intent"] == "director"
        assert result["found"] is True
        
        # Movie data
        assert result["movie"]["title"] == "The Matrix"
        assert result["movie"]["year"] == 1999
        
        # Crew directors
        assert len(result["crew"]) == 2
        director_names = [c["name"] for c in result["crew"]]
        assert "Lana Wachowski" in director_names
        assert "Lilly Wachowski" in director_names
        
        # Meta + source (fleksibel)
        assert result["source"] in ["db", "tmdb_ingest"]
        assert result["meta"]["used_year_filter"] is True

def test_answer_year_question(mock_tmdb_movie_data):
    """Step 4: Year wrapper end-to-end."""
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        from core_logic.qa_service import answer_year_question
        
        result = answer_year_question("The Matrix", year_hint=1999)
        
        # Intent & found
        assert result["intent"] == "year"
        assert result["found"] is True
        
        # Movie data
        assert result["movie"]["title"] == "The Matrix"
        assert result["movie"]["year"] == 1999
        
        # Tidak ada cast/crew
        assert "cast" not in result
        assert "crew" not in result
        
        # Meta + source
        assert result["source"] in ["db", "tmdb_ingest"]
        assert result["meta"]["used_year_filter"] is True


def test_answer_year_question_no_hint(mock_tmdb_movie_data):
    """Step 4: Year query tanpa year_hint."""
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        from core_logic.qa_service import answer_year_question
        
        result = answer_year_question("The Matrix")
        
        assert result["intent"] == "year"
        assert result["found"] is True
        assert result["movie"]["year"] == 1999
        assert result["meta"]["used_year_filter"] is False

def test_answer_cast_question(mock_tmdb_movie_data):
    """Step 5: Cast wrapper dengan intent/source/meta."""
    from core_logic.qa_service import answer_cast_question
    
    with patch.multiple('peninemate.tmdb_client', **mock_tmdb_movie_data):
        result = answer_cast_question("The Matrix", year=1999, top_cast=2)
        
        # Intent & found
        assert result["intent"] == "cast"
        assert result["found"] is True
        
        # Movie data
        assert result["movie"]["title"] == "The Matrix"
        assert result["movie"]["year"] == 1999
        
        # Cast data (struktur lama tetap)
        assert len(result["cast"]) == 2
        assert result["cast"][0]["actor"] == "Keanu Reeves"
        assert result["cast"][0]["character"] == "Neo"
        
        # Meta + source (field baru)
        assert result["source"] in ["db", "tmdb_ingest"]
        assert result["meta"]["used_year_filter"] is True
        assert result["meta"]["candidates_checked"] >= 1
