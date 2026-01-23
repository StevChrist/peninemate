"""
Backend Test Interface for PenineMate
Interactive testing for movie Q&A system
"""

# Load .env FIRST before any imports
from dotenv import load_dotenv
load_dotenv()

from peninemate.core_logic.qa_service import answer_question
from peninemate.infrastructure.db_client import get_conn
import sys

def check_database_connection():
    """Check if database is accessible and has data"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Check movies table
        cur.execute("SELECT COUNT(*) FROM movies")
        movie_count = cur.fetchone()[0]
        
        # Check credits table
        cur.execute("SELECT COUNT(*) FROM credits")
        credits_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print(f"✅ Database connected successfully")
        print(f"   - Movies: {movie_count:,}")
        print(f"   - Credits: {credits_count:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        print()
        print("⚠️  Please ensure database is running and data is imported.")
        return False


def run_test_suite():
    """Run predefined test questions"""
    
    test_questions = [
        # Director questions
        "Who directed Inception?",
        "Who is the director of The Dark Knight?",
        "Who made Interstellar?",
        
        # Cast questions
        "Who acted in Inception?",
        "Who are the actors in The Matrix?",
        "Cast of Pulp Fiction",
        
        # Plot questions
        "What is Inception about?",
        "Tell me about The Shawshank Redemption",
        "What is the plot of The Godfather?",
        
        # Year questions
        "When was Inception released?",
        "What year did The Matrix come out?",
        
        # Box office questions
        "How much did Inception earn?",
        "Box office of Avatar",
        
        # Filmography questions
        "Movies by Christopher Nolan",
        "Films directed by Quentin Tarantino",
        "Movies with Tom Hanks",
        
        # Semantic search
        "Science fiction heist movie",
        "Space exploration movies",
        "Movies about artificial intelligence",
    ]
    
    print("\n" + "=" * 60)
    print("🧪 RUNNING TEST SUITE")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n[{i}/{len(test_questions)}] {question}")
        
        try:
            result = answer_question(question)
            answer = result.get('answer', '')
            
            if answer and 'tidak ditemukan' not in answer.lower():
                print(f"✅ {answer[:100]}...")
                passed += 1
            else:
                print(f"❌ {answer}")
                failed += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(test_questions)}")
    print(f"❌ Failed: {failed}/{len(test_questions)}")
    print(f"📈 Accuracy: {(passed/len(test_questions)*100):.1f}%")
    print("=" * 60)


def interactive_mode():
    """Interactive Q&A mode"""
    print("\n" + "=" * 60)
    print("💬 INTERACTIVE MODE")
    print("=" * 60)
    print("Type your questions (or 'quit' to exit)")
    print()
    
    while True:
        try:
            question = input("🎬 Question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            result = answer_question(question)
            answer = result.get('answer', 'No answer found')
            source = result.get('source', 'unknown')
            
            print(f"🤖 Answer: {answer}")
            print(f"📍 Source: {source}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    print()
    print("=" * 60)
    print("🎬  PENINEMATE - BACKEND TEST INTERFACE")
    print("=" * 60)
    print("Test your movie Q&A backend system")
    print("=" * 60)
    print()
    
    # Check database connection
    if not check_database_connection():
        return
    
    # Menu
    print("\nSelect test mode:")
    print("1. Run automated test suite")
    print("2. Interactive Q&A mode")
    print("3. Both")
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    if choice == '1':
        run_test_suite()
    elif choice == '2':
        interactive_mode()
    elif choice == '3':
        run_test_suite()
        interactive_mode()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()
