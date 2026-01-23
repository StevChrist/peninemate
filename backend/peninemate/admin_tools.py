# peninemate/admin_tools.py (FIXED)

"""
Admin Tools - Database & FAISS Management
All-in-one utility for PenineMate administration
"""

import sys
from pathlib import Path

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from infrastructure.db_client import get_conn
from data_import.csv_importer import import_movies
from core_logic.faiss_builder import build_faiss_index
import json


# ============================================================
# DATABASE MANAGEMENT
# ============================================================

def clean_database():
    """Delete all movies from database."""
    conn = get_conn()
    cur = conn.cursor()
    
    print("🗑️  Cleaning movies table...")
    
    try:
        cur.execute("SELECT COUNT(*) FROM movies")
        before = cur.fetchone()[0]
        print(f"   📊 Movies before: {before}")
        
        cur.execute("TRUNCATE TABLE movies RESTART IDENTITY CASCADE;")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM movies")
        after = cur.fetchone()[0]
        print(f"   📊 Movies after: {after}")
        print("✅ Database cleaned!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()


def check_database():
    """Check database status."""
    conn = get_conn()
    cur = conn.cursor()
    
    print("=" * 60)
    print("📊 DATABASE STATUS")
    print("=" * 60)
    
    try:
        # Count movies
        cur.execute("SELECT COUNT(*) FROM movies")
        movie_count = cur.fetchone()[0]
        print(f"\n📽️  Total movies: {movie_count}")
        
        # Check credits
        cur.execute("SELECT COUNT(*) FROM credits")
        credits_count = cur.fetchone()[0]
        print(f"🎭 Total credits: {credits_count}")
        
        # Sample movies
        cur.execute("""
            SELECT title, year, data_source 
            FROM movies 
            ORDER BY id 
            LIMIT 5
        """)
        
        print(f"\n📋 Sample movies:")
        for row in cur.fetchall():
            print(f"   • {row[0]} ({row[1]}) - Source: {row[2]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()


# ============================================================
# FAISS MANAGEMENT
# ============================================================

def rebuild_faiss():
    """Rebuild FAISS index from database."""
    print("\n🔄 Rebuilding FAISS index...")
    
    # Delete old FAISS files
    data_dir = Path(__file__).parent / "data"
    index_path = data_dir / "faiss_movies.index"
    metadata_path = data_dir / "faiss_metadata.json"
    
    if index_path.exists():
        index_path.unlink()
        print(f"   🗑️  Deleted: {index_path.name}")
    
    if metadata_path.exists():
        metadata_path.unlink()
        print(f"   🗑️  Deleted: {metadata_path.name}")
    
    # Rebuild
    build_faiss_index()


def check_faiss():
    """Check FAISS index status."""
    data_dir = Path(__file__).parent / "data"
    index_path = data_dir / "faiss_movies.index"
    metadata_path = data_dir / "faiss_metadata.json"
    
    print("=" * 60)
    print("🔍 FAISS INDEX STATUS")
    print("=" * 60)
    
    if not index_path.exists():
        print("\n❌ FAISS index not found!")
        print(f"   Run: python peninemate/admin_tools.py rebuild")
        return
    
    if not metadata_path.exists():
        print("\n❌ FAISS metadata not found!")
        return
    
    # Load metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    print(f"\n✅ FAISS Index: {index_path.name}")
    print(f"   📊 Total vectors: {len(metadata)}")
    print(f"   📏 File size: {index_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Sample entries
    print(f"\n📋 Sample entries:")
    for m in metadata[:5]:
        print(f"   • {m['title']} ({m['year']}) - TMDb ID: {m['tmdb_id']}")


# ============================================================
# DATA IMPORT
# ============================================================

def import_data(limit=500, csv_file=None):
    """Import movies from CSV."""
    if csv_file is None:
        csv_file = Path(__file__).parent.parent / "dataset" / "enhanced_box_office_data(2000-2024).csv"
    
    print(f"\n📥 Importing {limit} movies from CSV...")
    print(f"   Source: {csv_file}")
    
    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        return 0
    
    count = import_movies(str(csv_file), limit=limit)
    print(f"✅ Imported {count} movies")
    return count


# ============================================================
# FULL OPERATIONS
# ============================================================

def full_reset(limit=500):
    """Full reset: clean DB → import data → rebuild FAISS."""
    print("=" * 60)
    print("🔄 FULL RESET")
    print("=" * 60)
    
    # Step 1: Clean database
    print("\n[1/3] Cleaning database...")
    clean_database()
    
    # Step 2: Import data
    print("\n[2/3] Importing data...")
    import_data(limit=limit)
    
    # Step 3: Rebuild FAISS
    print("\n[3/3] Rebuilding FAISS...")
    rebuild_faiss()
    
    print("\n" + "=" * 60)
    print("✅ FULL RESET COMPLETE!")
    print("=" * 60)


def status():
    """Show complete system status."""
    check_database()
    print()
    check_faiss()


# ============================================================
# CLI INTERFACE
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PenineMate Admin Tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python admin_tools.py status              # Show system status
  python admin_tools.py clean               # Clean database
  python admin_tools.py import --limit 1000 # Import 1000 movies
  python admin_tools.py rebuild             # Rebuild FAISS index
  python admin_tools.py reset --limit 5000  # Full reset with 5000 movies
        """
    )
    
    parser.add_argument('action', 
                        choices=['status', 'clean', 'rebuild', 'import', 'reset', 'check-db', 'check-faiss'],
                        help='Action to perform')
    parser.add_argument('--limit', type=int, default=500,
                        help='Number of movies to import (default: 500)')
    parser.add_argument('--csv', type=str, default=None,
                        help='Path to CSV file (optional)')
    
    args = parser.parse_args()
    
    if args.action == 'status':
        status()
    elif args.action == 'clean':
        clean_database()
    elif args.action == 'rebuild':
        rebuild_faiss()
    elif args.action == 'import':
        import_data(limit=args.limit, csv_file=args.csv)
    elif args.action == 'reset':
        full_reset(limit=args.limit)
    elif args.action == 'check-db':
        check_database()
    elif args.action == 'check-faiss':
        check_faiss()
