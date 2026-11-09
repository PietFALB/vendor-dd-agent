"""Search the guidance corpus and return chunks with their source and page."""
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

INDEX_NAME = "vendor-dd-guidance"

_store = PineconeVectorStore(
    index_name=INDEX_NAME,
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Return the k most relevant guidance chunks for a query."""
    results = _store.similarity_search_with_score(query, k=k)
    return [
        {
            "text": doc.page_content,
            "source": doc.metadata.get("source"),
            "page": int(doc.metadata.get("page", 0)),
            "score": round(score, 3),
        }
        for doc, score in results
    ]


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "What makes ownership by a sanctioned person a red flag?"
    for hit in retrieve(question):
        print(f"\n[{hit['source']} p.{hit['page']}] score={hit['score']}")
        print(hit["text"][:300], "...")
