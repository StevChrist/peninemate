# enrich_all_movielens.py

from dotenv import load_dotenv
load_dotenv()

from peninemate.infrastructure.db_client import get_conn
from peninemate.infrastructure.tmdb_client import get_tmdb_client
import time
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
MAX_MOVIES_TO_ENRICH = 12,657  # Maximum movies to process
DELAY_BETWEEN_REQUESTS = 2.0  # Seconds between each API call (conservative)
BATCH_COMMIT_SIZE = 100       # Commit to DB every N movies
PROGRESS_REPORT_INTERVAL = 100 # Show progress every N movies

print("=" * 80)
print("ENRICHING MOVIELENS MOVIES WITH TMDB DATA")
print("=" * 80)
print(f"\n⚙️  Configuration:")
print(f"   Max movies to enrich: {MAX_MOVIES_TO_ENRICH:,}")
print(f"   Delay between requests: {DELAY_BETWEEN_REQUESTS}s")
print(f"   Batch commit size: {BATCH_COMMIT_SIZE}")
print(f"   Progress report: Every {PROGRESS_REPORT_INTERVAL} movies")

conn = get_conn()
cur = conn.cursor()

# Get movies without overview (prioritize popular ones)
print("\n🔍 Finding movies to enrich...")
cur.execute("""
    SELECT tmdb_id, title, year
    FROM movies 
    WHERE (overview IS NULL OR overview = '')
    ORDER BY 
        -- Prioritize movies with popularity (most requested first)
        CASE WHEN popularity IS NOT NULL THEN 0 ELSE 1 END,
        popularity DESC NULLS LAST
    LIMIT %s
""", (MAX_MOVIES_TO_ENRICH,))

movies_to_enrich = cur.fetchall()
total_movies = len(movies_to_enrich)

print(f"   Found {total_movies:,} movies to enrich")

if total_movies == 0:
    print("\n✅ No movies need enrichment!")
    cur.close()
    conn.close()
    exit(0)

# Estimate time
estimated_time_seconds = total_movies * DELAY_BETWEEN_REQUESTS
estimated_time_minutes = estimated_time_seconds / 60
estimated_time_hours = estimated_time_minutes / 60

print(f"\n⏱️  Estimated time:")
print(f"   {estimated_time_minutes:.1f} minutes ({estimated_time_hours:.2f} hours)")
print(f"   Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Expected finish: {datetime.fromtimestamp(time.time() + estimated_time_seconds).strftime('%Y-%m-%d %H:%M:%S')}")

# Ask for confirmation
print(f"\n⚠️  This will make {total_movies:,} API calls to TMDb")
print(f"   At {DELAY_BETWEEN_REQUESTS}s per request, this will take ~{estimated_time_hours:.2f} hours")
confirm = input("\nContinue? (yes/no): ")

if confirm.lower() != 'yes':
    print("❌ Enrichment cancelled")
    cur.close()
    conn.close()
    exit(0)

# ============================================================
# START ENRICHMENT WITH DETAILED PROGRESS
# ============================================================

tmdb_client = get_tmdb_client()
enriched = 0
errors = 0
skipped = 0
rate_limit_waits = 0

print(f"\n💾 Starting enrichment...")
print(f"{'=' * 80}")
start_time = time.time()

def format_time(seconds):
    """Format seconds to human readable time"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def get_progress_bar(current, total, width=40):
    """Generate a text progress bar"""
    progress = current / total
    filled = int(width * progress)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {progress * 100:.1f}%"

for idx, (tmdb_id, title, year) in enumerate(movies_to_enrich, 1):
    try:
        # Fetch details from TMDb
        details = tmdb_client.get_movie_details(tmdb_id)
        
        if details and details.get('overview'):
            # Update database
            cur.execute("""
                UPDATE movies 
                SET overview = %s,
                    popularity = COALESCE(popularity, %s)
                WHERE tmdb_id = %s
            """, (
                details.get('overview'),
                details.get('popularity'),
                tmdb_id
            ))
            
            enriched += 1
            
            # Batch commit
            if enriched % BATCH_COMMIT_SIZE == 0:
                conn.commit()
            
            # Progress report every PROGRESS_REPORT_INTERVAL movies
            if idx % PROGRESS_REPORT_INTERVAL == 0:
                elapsed = time.time() - start_time
                avg_per_movie = elapsed / idx
                remaining = total_movies - idx
                eta_seconds = remaining * avg_per_movie
                
                progress_pct = (idx / total_movies) * 100
                finish_time = datetime.fromtimestamp(time.time() + eta_seconds).strftime('%H:%M:%S')
                speed = (enriched / elapsed) * 60 if elapsed > 0 else 0
                
                # Progress bar
                progress_bar = get_progress_bar(idx, total_movies)
                
                print(f"\n{'─' * 80}")
                print(f"📊 PROGRESS UPDATE")
                print(f"{'─' * 80}")
                print(f"   {progress_bar}")
                print(f"   Processed: {idx:,} / {total_movies:,} movies ({progress_pct:.1f}%)")
                print(f"   Enriched: {enriched:,} | Skipped: {skipped:,} | Errors: {errors:,}")
                print(f"   Speed: {speed:.1f} movies/min")
                print(f"   Elapsed: {format_time(elapsed)}")
                print(f"   ETA: {format_time(eta_seconds)} (finish ~{finish_time})")
                print(f"   Current: {title[:60]}...")
                print(f"{'─' * 80}")
            
            # Conservative rate limiting
            time.sleep(DELAY_BETWEEN_REQUESTS)
        else:
            skipped += 1
            time.sleep(DELAY_BETWEEN_REQUESTS / 2)
    
    except Exception as e:
        errors += 1
        error_msg = str(e)
        
        # Handle rate limiting (429 Too Many Requests)
        if "429" in error_msg:
            rate_limit_waits += 1
            wait_time = min(30, rate_limit_waits * 5)
            print(f"\n   ⚠️  Rate limit hit (#{rate_limit_waits}), waiting {wait_time}s...")
            time.sleep(wait_time)
            
            # Retry this movie
            try:
                details = tmdb_client.get_movie_details(tmdb_id)
                if details and details.get('overview'):
                    cur.execute("""
                        UPDATE movies 
                        SET overview = %s, popularity = COALESCE(popularity, %s)
                        WHERE tmdb_id = %s
                    """, (details.get('overview'), details.get('popularity'), tmdb_id))
                    enriched += 1
                    errors -= 1
                    print(f"   ✅ Retry successful for: {title}")
            except:
                print(f"   ❌ Retry failed for: {title}")
        else:
            # Log other errors occasionally
            if errors % 50 == 1:
                print(f"   ⚠️  Error #{errors}: {title} (tmdb_id: {tmdb_id}) - {error_msg[:50]}")
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
        continue

# Final commit
conn.commit()

# Calculate final stats
elapsed_total = time.time() - start_time
elapsed_minutes = elapsed_total / 60
elapsed_hours = elapsed_minutes / 60

print(f"\n{'=' * 80}")
print(f"✅ ENRICHMENT COMPLETE!")
print(f"{'=' * 80}")

print(f"\n📊 Final Statistics:")
print(f"   Total processed: {total_movies:,}")
print(f"   Successfully enriched: {enriched:,} ({enriched/total_movies*100:.1f}%)")
print(f"   Skipped (no overview in TMDb): {skipped:,}")
print(f"   Errors: {errors:,}")
print(f"   Rate limit waits: {rate_limit_waits}")

print(f"\n⏱️  Time Statistics:")
print(f"   Total time: {format_time(elapsed_total)} ({elapsed_hours:.2f} hours)")
print(f"   Average per movie: {elapsed_total/total_movies:.2f}s")
print(f"   Average speed: {(enriched/elapsed_total)*60:.1f} movies/min")
print(f"   Finish time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Verify enrichment
print(f"\n🔍 Verifying database...")
cur.execute("SELECT COUNT(*) FROM movies WHERE overview IS NOT NULL AND overview != ''")
total_with_overview = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM movies")
total_all_movies = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM movies WHERE overview IS NULL OR overview = ''")
remaining_without_overview = cur.fetchone()[0]

print(f"   Movies with overview: {total_with_overview:,} / {total_all_movies:,} ({total_with_overview/total_all_movies*100:.1f}%)")
print(f"   Still need overview: {remaining_without_overview:,}")

cur.close()
conn.close()

print(f"\n💡 Next steps:")
print(f"   1. Rebuild FAISS index: python peninemate/core_logic/faiss_builder.py")
print(f"   2. Restart API: python run_api.py")
if remaining_without_overview > 0:
    print(f"   3. (Optional) Run enrichment again to process remaining {remaining_without_overview:,} movies")
print(f"{'=' * 80}")
