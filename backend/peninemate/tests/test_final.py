# test_final.py
from peninemate.qa_llm import answer_movie_question

print("=" * 60)
print("🎬 PenineMate - Movie Q&A System")
print("=" * 60)

questions = [
    "Siapa sutradara The Matrix?",
    "Kapan Inception rilis?",
    "Siapa pemain Interstellar?",
    "Kapan film Avatar rilis?",
    "Siapa sutradara Oppenheimer?",
]

for q in questions:
    print(f"\n❓ {q}")
    answer = answer_movie_question(q)
    print(f"✅ {answer}")
    print("-" * 60)
