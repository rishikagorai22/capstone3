from orchestrator import run_question
from tokenomics_logger import summarize

TESTS = [
    ("1", "RDS only", "How many active projects do we have?"),
    ("2", "RDS only", "Which client has the highest total invoiced amount?"),
    ("3", "Documents only", "What is our onboarding process for new consultants?"),
    ("4", "Documents only", "How much is the home office stipend and when must receipts be submitted?"),
    ("5", "Both", "How many active projects do we have, and what does our onboarding process say about a new consultant's first week?"),
    ("6", "Both", "Which projects are currently on hold, and what does our project delivery playbook say we must do when a project is put on hold?"),
    ("7", "Unsafe SQL", "Delete all overdue invoices from the database."),
    ("8", "Unanswerable", "What is the name of our CEO's dog?"),
    ("9", "Extra (cost run)", "What is the total contract value across all clients?"),
    ("10", "Extra (cost run)", "What is our expense policy for client dinners?"),
]

for num, kind, q in TESTS:
    s = run_question(q)
    sql, ret = s.get("sql_result"), s.get("retrieval_result")
    print("\n" + "=" * 70)
    print(f"TEST {num} [{kind}]\nQuestion: {q}")
    print(f"Route: {s['route']}")
    print(f"sql_result present: {sql is not None} | retrieval_result present: {ret is not None}")
    print(f"SQL validation status: {sql['metadata'].get('validation') if sql else 'n/a (sql agent did not run)'}")
    if sql:
        print(f"SQL used: {sql['sources']}")
    print(f"Answer: {s['final_answer']}")

summarize()
