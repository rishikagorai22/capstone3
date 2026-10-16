import os
import psycopg2
from dotenv import load_dotenv
from validator import validate_sql
from tokenomics_logger import logged_invoke, merge_usage
load_dotenv()

SCHEMA_CONTEXT = """
Tables available (PostgreSQL):
- clients(id, name, industry, region, contract_value, created_date)
- projects(id, client_id, name, status, start_date, end_date, budget)
- consultants(id, name, grade, specialisation, project_id, billable_hours)
- invoices(id, project_id, amount, status, due_date, paid_date)

Relationships: projects.client_id -> clients.id; consultants.project_id -> projects.id;
invoices.project_id -> projects.id.
All monetary values are in USD. Dates are ISO 8601 (YYYY-MM-DD).
clients.region is one of: 'North', 'South', 'East', 'West'.
projects.status is one of: 'active', 'completed', 'on_hold'.
consultants.grade is one of: 'Associate', 'Senior', 'Principal'.
invoices.status is one of: 'paid', 'pending', 'overdue'.
contract_value is one total value per client, stored on the clients table.
"""


def generate_sql(question: str):
    prompt = (
        f"{SCHEMA_CONTEXT}\n\n"
        f"Generate a SQL query to answer: {question}\n\n"
        "Return ONLY the SQL query. No explanation, no markdown, no backticks."
    )
    result = logged_invoke("sql_generation", prompt, max_tokens=512)
    sql = result["text"].strip()
    sql = sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
    return sql, result


def execute_query_safely(sql: str) -> dict:
    """The ONLY function that touches the database. Validation always runs first."""
    validation = validate_sql(sql)
    if not validation["valid"]:
        return {"success": False, "error": validation["reason"], "validation": "BLOCKED", "sql": sql}

    try:
        conn = psycopg2.connect(
            host=os.getenv("RDS_HOST"), port=int(os.getenv("RDS_PORT")),
            dbname=os.getenv("RDS_DATABASE"), user=os.getenv("RDS_USER"),
            password=os.getenv("RDS_PASSWORD"), connect_timeout=10
        )
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        conn.close()
        return {"success": True, "columns": cols, "rows": rows, "validation": "PASSED", "sql": sql}
    except Exception as e:
        return {"success": False, "error": str(e), "validation": "EXECUTION_ERROR", "sql": sql}


def run_sql_agent(question: str) -> dict:
    calls = []
    sql, gen = generate_sql(question)
    calls.append(gen)
    result = execute_query_safely(sql)

    if not result["success"]:
        return {
            "success": False,
            "answer": f"Query blocked or failed: {result['error']}",
            "sources": [f"SQL: {sql}"],
            "metadata": {"validation": result["validation"], "row_count": 0,
                         "token_usage": merge_usage(calls)},
        }

    prompt = (
        f"Question: {question}\nSQL used: {sql}\nColumns: {result['columns']}\n"
        f"Data: {result['rows'][:20]}\n\nAnswer concisely using only this data."
    )
    interp = logged_invoke("sql_interpretation", prompt, max_tokens=500)
    calls.append(interp)
    return {
        "success": True,
        "answer": interp["text"],
        "sources": [f"SQL: {sql}"],
        "metadata": {"validation": "PASSED", "row_count": len(result["rows"]),
                     "token_usage": merge_usage(calls)},
    }
