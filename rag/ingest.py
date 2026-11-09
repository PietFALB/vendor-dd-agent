"""Load guidance PDFs, split into chunks, and upload to Pinecone."""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

INDEX_NAME = "vendor-dd-guidance"
CORPUS_DIR = Path("data/corpus")


def main():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,  # size of text-embedding-3-small vectors
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"Created index {INDEX_NAME}")

    docs = []
    for pdf in sorted(CORPUS_DIR.glob("*.pdf")):
        pages = PyPDFLoader(str(pdf)).load()
        for p in pages:
            p.metadata = {"source": pdf.name, "page": p.metadata.get("page", 0) + 1}
        docs.extend(pages)
        print(f"Loaded {pdf.name}: {len(pages)} pages")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks, uploading...")

    PineconeVectorStore.from_documents(
        chunks,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        index_name=INDEX_NAME,
    )
    print("Done.")


if __name__ == "__main__":
    main()
