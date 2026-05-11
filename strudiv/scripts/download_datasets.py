import wikipedia
import arxiv
import random
import nltk
from typing import List

# =========================
# Utils
# =========================

def split_sentences(text: str) -> List[str]:
    sentences = nltk.sent_tokenize(text)
    return [s.strip() for s in sentences if len(s.split()) > 5]


# =========================
# Wikipedia Facts
# =========================

def get_wikipedia_facts(topics: List[str], max_sentences=5) -> List[str]:
    facts = []

    for topic in topics:
        try:
            page = wikipedia.page(topic, auto_suggest=False)
            summary = page.summary

            sentences = split_sentences(summary)

            facts.extend(sentences[:max_sentences])

        except Exception as e:
            print(f"[Wikipedia Error] {topic}: {e}")

    return facts


# =========================
# arXiv Facts
# =========================

def get_arxiv_facts(query="machine learning", max_results=3) -> List[str]:
    facts = []

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    for result in search.results():
        abstract = result.summary

        sentences = split_sentences(abstract)

        # 过滤太 technical 或带公式的句子（简单规则）
        clean_sentences = [
            s for s in sentences
            if "$" not in s and len(s) < 200
        ]

        facts.extend(clean_sentences[:3])

    return facts


# =========================
# Main Fact Collector
# =========================

def collect_facts() -> List[str]:
    """
    从 Wikipedia + arXiv 获取真实 facts
    """

    # 你可以控制 topic（很重要！）
    wiki_topics = [
        "Eiffel Tower",
        "France",
        "Berlin",
        "Water",
        "Electricity"
    ]

    print("\n[Collecting Wikipedia Facts...]")
    wiki_facts = get_wikipedia_facts(wiki_topics)

    print("\n[Collecting arXiv Facts...]")
    arxiv_facts = get_arxiv_facts(query="artificial intelligence")

    all_facts = wiki_facts + arxiv_facts

    # 打乱（避免结构偏置）
    random.shuffle(all_facts)

    print("\n[Collected Facts]:")
    for f in all_facts:
        print("-", f)

    return all_facts


# =========================
# Test
# =========================

if __name__ == "__main__":
    facts = collect_facts()
    print(f"\nTotal Facts: {len(facts)}")