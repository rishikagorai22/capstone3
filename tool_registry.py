from agents.sql_agent import run_sql_agent
from agents.retrieval_agent import run_retrieval_agent

TOOL_REGISTRY = {
    "sql_agent": {
        "function": run_sql_agent,
        "schema": {
            "name": "sql_agent",
            "description": (
                "Query the relational PostgreSQL database for structured, numeric, or categorical data "
                "about clients, projects, consultants, and invoices: counts, totals, averages, statuses, "
                "budgets, billing, and comparisons. Read-only. NOT for policies, procedures, guidelines, "
                "or narrative document content, and it cannot modify data."),
            "input_schema": {"type": "object", "properties": {"question": {"type": "string"}},
                             "required": ["question"]},
        },
    },
    "retrieval_agent": {
        "function": run_retrieval_agent,
        "schema": {
            "name": "retrieval_agent",
            "description": (
                "Search the indexed company documents for policy, procedure, and playbook information: "
                "onboarding, expense reimbursement, remote work, and project delivery guidance. "
                "NOT for counts, totals, or any live figures that live in the database."),
            "input_schema": {"type": "object", "properties": {"question": {"type": "string"}},
                             "required": ["question"]},
        },
    },
}


def get_all_schemas() -> list:
    return [t["schema"] for t in TOOL_REGISTRY.values()]


def call_tool(tool_name: str, question: str) -> dict:
    if tool_name not in TOOL_REGISTRY:
        return {"success": False, "answer": f"Unknown tool: {tool_name}", "sources": [], "metadata": {}}
    try:
        return TOOL_REGISTRY[tool_name]["function"](question)
    except Exception as e:
        return {"success": False, "answer": f"Tool error: {e}", "sources": [], "metadata": {"error": str(e)}}
