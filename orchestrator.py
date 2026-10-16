from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from tokenomics_logger import logged_invoke
from tool_registry import get_all_schemas, call_tool
load_dotenv()


class OrchestratorState(TypedDict):
    question: str
    route: Optional[str]            # "sql", "retrieval", or "both"
    sql_result: Optional[dict]
    retrieval_result: Optional[dict]
    final_answer: Optional[str]
    token_usage: Optional[dict]


def _usage(result: dict) -> dict:
    return {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"],
            "cost_usd": result["cost_usd"]}


def _add(state, component, usage):
    tu = dict(state.get("token_usage") or {})
    tu[component] = usage
    return tu


def _with_total(tu: dict) -> dict:
    parts = [v for k, v in tu.items() if k != "total"]
    tu = dict(tu)
    tu["total"] = {"input_tokens": sum(p["input_tokens"] for p in parts),
                   "output_tokens": sum(p["output_tokens"] for p in parts),
                   "cost_usd": sum(p["cost_usd"] for p in parts)}
    return tu


def route_question(state: OrchestratorState) -> OrchestratorState:
    tools = "\n".join(f"- {s['name']}: {s['description']}" for s in get_all_schemas())
    prompt = (
        f"Available tools:\n{tools}\n\nQuestion: {state['question']}\n\n"
        "Decide which tool(s) are needed to fully answer the question. Reply with exactly one word:\n"
        "sql (only sql_agent), retrieval (only retrieval_agent), or both "
        "(needs database figures AND document information).\n"
        "If the question asks to change or delete data, reply sql. If neither tool fits, reply retrieval."
    )
    result = logged_invoke("classification", prompt, max_tokens=10)
    word = result["text"].strip().lower()
    route = "both" if "both" in word else "sql" if "sql" in word else "retrieval"
    return {**state, "route": route, "token_usage": _add(state, "classification", _usage(result))}


def call_sql_agent(state: OrchestratorState) -> OrchestratorState:
    if state["route"] not in ("sql", "both"):
        return state
    result = call_tool("sql_agent", state["question"])
    tu = state.get("token_usage") or {}
    used = result.get("metadata", {}).get("token_usage")
    if used:
        tu = _add(state, "sql_agent", used)
    return {**state, "sql_result": result, "token_usage": tu}


def call_retrieval_agent(state: OrchestratorState) -> OrchestratorState:
    if state["route"] not in ("retrieval", "both"):
        return state
    result = call_tool("retrieval_agent", state["question"])
    tu = state.get("token_usage") or {}
    used = result.get("metadata", {}).get("token_usage")
    if used:
        tu = _add(state, "retrieval_agent", used)
    return {**state, "retrieval_result": result, "token_usage": tu}


def synthesise(state: OrchestratorState) -> OrchestratorState:
    sql, ret = state.get("sql_result"), state.get("retrieval_result")
    context, notes = "", []

    if sql and sql.get("success"):
        context += f"SQL Agent result:\n{sql['answer']}\nSource: {sql['sources']}\n\n"
    elif sql:
        notes.append(f"The SQL Agent could not answer: {sql['answer']}")
    if ret and ret.get("success"):
        context += f"Retrieval Agent result:\n{ret['answer']}\nSources: {ret['sources']}\n\n"
    elif ret:
        notes.append(f"The Retrieval Agent could not answer: {ret['answer']}")

    if not context:
        if sql and sql.get("metadata", {}).get("validation") == "BLOCKED":
            answer = ("I can't do that. This system only runs read-only SELECT queries, and this request "
                      "was blocked by the SQL validation layer before it reached the database.")
        else:
            answer = "I couldn't find information to answer this question in the database or the documents."
        return {**state, "final_answer": answer, "token_usage": _with_total(state.get("token_usage") or {})}

    prompt = (
        "Answer the question using ONLY the information below. Attribute each fact to the agent it came "
        "from, for example '(SQL Agent)' or '(Retrieval Agent: filename)'. Do not add facts that are not "
        "present. If part of the question could not be answered, say so plainly.\n\n"
        f"Question: {state['question']}\n\nInformation:\n{context}"
        + ("\nNotes:\n" + "\n".join(notes) if notes else "")
    )
    result = logged_invoke("synthesis", prompt, max_tokens=800)
    return {**state, "final_answer": result["text"].strip(),
            "token_usage": _with_total(_add(state, "synthesis", _usage(result)))}


def build_orchestrator():
    graph = StateGraph(OrchestratorState)
    graph.add_node("router", route_question)
    graph.add_node("sql_agent", call_sql_agent)
    graph.add_node("retrieval_agent", call_retrieval_agent)
    graph.add_node("synthesiser", synthesise)
    graph.set_entry_point("router")
    graph.add_edge("router", "sql_agent")
    graph.add_edge("sql_agent", "retrieval_agent")
    graph.add_edge("retrieval_agent", "synthesiser")
    graph.add_edge("synthesiser", END)
    return graph.compile()


orchestrator = build_orchestrator()


def run_question(question: str) -> dict:
    return orchestrator.invoke({"question": question, "route": None, "sql_result": None,
                                "retrieval_result": None, "final_answer": None, "token_usage": None})


if __name__ == "__main__":
    for q in ["How many active projects do we have?",
              "What is our onboarding process for new consultants?",
              "How many active projects do we have, and what is our onboarding process?"]:
        s = run_question(q)
        print(f"\n{'=' * 60}\nQ: {q}\nRoute: {s['route']}\nAnswer: {s['final_answer']}\n"
              f"Total tokens: {s['token_usage']['total']}")
