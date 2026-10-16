import os, boto3
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
load_dotenv()
c = boto3.Session().get_credentials()
auth = AWS4Auth(c.access_key, c.secret_key, "us-east-1", "es", session_token=c.token)
client = OpenSearch(hosts=[{"host": os.getenv("OPENSEARCH_ENDPOINT"), "port": 443}],
                    http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection)
try:
    print("documents index count:", client.count(index="documents")["count"])
    resp = client.search(index="documents", body={"size": 100, "_source": ["source"], "query": {"match_all": {}}})
    print("sources:", sorted({h["_source"]["source"] for h in resp["hits"]["hits"]}))
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:300])
