import os, glob, boto3
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from onnx_embed import embed
load_dotenv()

INDEX_NAME = "documents"
CHUNK_WORDS, OVERLAP = 300, 40   # small chunks keep each embedding focused; overlap avoids cutting facts in half


def get_client():
    c = boto3.Session().get_credentials()
    auth = AWS4Auth(c.access_key, c.secret_key, "us-east-1", "es", session_token=c.token)
    return OpenSearch(hosts=[{"host": os.getenv("OPENSEARCH_ENDPOINT"), "port": 443}],
                      http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection)


def chunk_text(text):
    words = text.split()
    return [" ".join(words[i:i + CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS - OVERLAP)
            if words[i:i + CHUNK_WORDS]]


client = get_client()
if not client.indices.exists(index=INDEX_NAME):
    client.indices.create(index=INDEX_NAME, body={
        "settings": {"index.knn": True},
        "mappings": {"properties": {
            "content": {"type": "text"},
            "source": {"type": "keyword"},
            "chunk_number": {"type": "integer"},
            "embedding": {"type": "knn_vector", "dimension": 384,
                          "method": {"name": "hnsw", "space_type": "innerproduct", "engine": "faiss"}}}}})
    print("Created index")

for path in sorted(glob.glob("docs/*.txt")):
    source = os.path.basename(path)
    chunks = chunk_text(open(path).read())
    vectors = embed(chunks)
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        client.index(index=INDEX_NAME, id=f"{source}-{i}",
                     body={"content": chunk, "embedding": vec, "source": source, "chunk_number": i})
    print(f"Indexed {len(chunks)} chunks from {source}")

client.indices.refresh(index=INDEX_NAME)
print("OpenSearch documents index count:", client.count(index=INDEX_NAME)["count"])
