# Unit 3 Capstone: Multi-Agent System on AWS (Bronze)

A LangGraph orchestrator that routes questions about a consulting firm to a SQL agent (RDS PostgreSQL), a retrieval agent (OpenSearch), or both, then synthesizes one cited answer. Claude is called through Amazon Bedrock. Deployed as an AWS Lambda function.

## Code
- `orchestrator.py`: LangGraph state graph (classification, SQL node, retrieval node, synthesis)
- `agents/sql_agent.py`, `agents/retrieval_agent.py`: tool wrappers (shared `success/answer/sources/metadata` interface)
- `tool_registry.py`: shared tool registry with scoped descriptions
- `validator.py`: SQL validator and test suite (whole-word keyword match, SELECT-only, independent stacked-query check)
- `tokenomics_logger.py`: per-call token and USD cost logging and summary
- `lambda_handler.py`: Lambda entry point
- `bedrock_client.py`, `onnx_embed.py`: Bedrock helper, ONNX MiniLM embeddings (384 dims)
- `ingest_docs.py`, `docs/`: document ingestion into OpenSearch
- `run_tests.py`: the 8 required questions plus 2 extras for the 10-query cost run

## Evidence (`evidence/`)
- `validator_test_output.txt`: SQL validation test suite
- `step5_direct_block_output.txt`: unsafe SQL fed straight to the executor, blocked
- `test_results.txt`: results for the 8 test questions (plus 2 extras) and the cost table
- `tokenomics_summary.txt`: 10-query cost summary
- `response.json`, `cloudwatch_lines.txt`: deployed Lambda run for a question routed to `both`
- `step1_*`, `step2_*`: data store and interface checks

## Reflection
See `capstone_3_reflection.md`.

## Setup notes
Copy `.env.example` to `.env` and fill in your own values. Download `model.onnx` and `tokenizer.json` from the `sentence-transformers/all-MiniLM-L6-v2` page on Hugging Face (they are not committed because of size). Secrets and deployment packages are excluded via `.gitignore`.
