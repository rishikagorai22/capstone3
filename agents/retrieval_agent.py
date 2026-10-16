import os, re, boto3
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from onnx_embed import get_embedding
from tokenomics_logger import logged_invoke, merge_usage
load_dotenv()

INDEX_NAME = "documents"


def get_opensearch_client():
    c = boto3.Session().get_credentials()
    auth = AWS4Auth(c.access_key, c.secret_key, "us-east-1", "es", session_token=c.token)
    return OpenSearch(hosts=[{"host": os.getenv("OPENSEARCH_ENDPOINT"), "port": 443}],
                      http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection)


def retrieve(question: str, top_k: int = 5) -> list:
    vec = get_embedding(question)
    resp = get_opensearch_client().search(index=INDEX_NAME, body={
        "size": top_k, "query": {"knn": {"embedding": {"vector": vec, "k": top_k}}}})
    return [{"content": h["_source"]["content"], "source": h["_source"]["source"], "score": h["_score"]}
            for h in resp["hits"]["hits"]]


def check_grounding(answer: str, chunks: list) -> bool:
    cited = re.findall(r"Source (\d+)", answer)
    if not cited:
        return "cannot find" in answer.lower()
    return all(1 <= int(s) <= len(chunks) for s in cited)


def run_retrieval_agent(question: str) -> dict:
    calls = []
    try:
        chunks = retrieve(question)
    except Exception as e:
        return {"success": False, "answer": f"Document search failed: {e}", "sources": [],
                "metadata": {"error": str(e), "token_usage": merge_usage([])}}
    if not chunks:
        return {"success": False, "answer": "No relevant documents found.", "sources": [],
                "metadata": {"chunk_count": 0, "token_usage": merge_usage([])}}

    context = "\n\n".join(f"[Source {i+1}: {c['source']}]\n{c['content']}" for i, c in enumerate(chunks))
    prompt = (
        "Answer the question using ONLY the context provided below. "
        "If the answer is not in the context, reply exactly: "
        "'I cannot find this information in the provided documents.' "
        "After each fact, cite the source like [Source 2].\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
    )
    gen = logged_invoke("retrieval_answer_generation", prompt, max_tokens=500)
    calls.append(gen)
    answer = gen["text"].strip()
    refused = "cannot find this information" in answer.lower()
    return {
        "success": not refused,
        "answer": answer,
        "sources": [] if refused else list(dict.fromkeys(c["source"] for c in chunks)),
        "metadata": {"chunk_count": len(chunks),
                     "chunk_scores": [round(c["score"], 3) for c in chunks],
                     "grounded": check_grounding(answer, chunks),
                     "refused": refused,
                     "token_usage": merge_usage(calls)},
    }
