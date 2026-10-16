import json
from orchestrator import run_question


def handler(event, context):
    try:
        body = event.get("body") if isinstance(event, dict) else None
        if isinstance(body, str):
            body = json.loads(body)
        elif body is None:
            body = event
        question = ((body or {}).get("question") or "").strip()
        if not question:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing 'question' in request body"})}

        state = run_question(question)
        sql, ret = state.get("sql_result"), state.get("retrieval_result")
        payload = {
            "question": question,
            "route": state["route"],
            "sql_validation": sql["metadata"].get("validation") if sql else None,
            "answer": state["final_answer"],
            "sql_sources": sql["sources"] if sql else [],
            "retrieval_sources": ret["sources"] if ret else [],
            "token_usage": state["token_usage"],
        }
        print("RESULT " + json.dumps({"route": payload["route"],
                                      "sql_validation": payload["sql_validation"],
                                      "token_usage_total": (state["token_usage"] or {}).get("total")}))
        return {"statusCode": 200, "body": json.dumps(payload, default=str)}
    except Exception as e:
        print(f"ERROR {type(e).__name__}: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal error processing the request."})}
