from agents.sql_agent import run_sql_agent
from agents.retrieval_agent import run_retrieval_agent

r1 = run_sql_agent("How many active projects do we have?")
r2 = run_retrieval_agent("What is our onboarding process for new consultants?")
print("SQL agent top-level keys:      ", list(r1.keys()))
print("Retrieval agent top-level keys:", list(r2.keys()))
print("\nSQL answer:", r1["answer"])
print("Retrieval answer:", r2["answer"])
