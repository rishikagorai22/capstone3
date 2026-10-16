import re

BLOCKED_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
                    "EXEC", "EXECUTE", "GRANT", "REVOKE"]


def _strip_comments(query: str) -> str:
    query = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    query = re.sub(r"--[^\n]*", " ", query)
    return query


def validate_sql(query: str) -> dict:
    cleaned = _strip_comments(query).strip()
    upper = cleaned.upper()

    # Step 1: blocked keywords, whole words only (deleted_at is NOT blocked)
    for keyword in BLOCKED_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            return {"valid": False,
                    "reason": f"Blocked: '{keyword}' is not permitted. Only SELECT queries are allowed."}

    # Step 2: must be a SELECT
    if not upper.startswith("SELECT"):
        return {"valid": False,
                "reason": "Only SELECT queries are permitted. Query must begin with SELECT."}

    # Step 3: stacked statements, checked independently of keywords.
    # One trailing semicolon is fine; any other semicolon means multiple statements.
    body = cleaned.rstrip(";").strip()
    if ";" in body:
        return {"valid": False,
                "reason": "Blocked: multiple statements detected (possible stacked query attempt)."}

    return {"valid": True, "reason": "OK"}


TEST_CASES = [
    ("valid SELECT", "SELECT * FROM clients WHERE region = 'North'", True),
    ("DROP blocked", "DROP TABLE clients", False),
    ("DELETE blocked", "DELETE FROM projects WHERE status = 'active'", False),
    ("UPDATE blocked", "UPDATE consultants SET grade = 'Senior'", False),
    ("INSERT blocked", "INSERT INTO invoices VALUES (1, 100, 'paid')", False),
    ("column deleted_at allowed (whole word match)", "SELECT deleted_at FROM projects", True),
    ("stacked WITH keyword blocked", "SELECT * FROM projects; DROP TABLE clients;", False),
    ("stacked, NO keyword, blocked (proves stacking check is independent)",
     "SELECT * FROM projects; SELECT * FROM clients", False),
    ("single trailing semicolon allowed", "SELECT * FROM clients;", True),
    ("mixed case blocked", "DeLeTe FROM projects", False),
    ("newline-separated stacked blocked", "SELECT * FROM projects;\nDROP TABLE clients", False),
]


def run_test_suite() -> bool:
    print("=" * 70)
    print("VALIDATOR TEST SUITE")
    print("=" * 70)
    all_passed = True
    for label, query, expected in TEST_CASES:
        result = validate_sql(query)
        passed = result["valid"] == expected
        all_passed = all_passed and passed
        print(f"[{'PASS' if passed else 'FAIL'}] {label}: valid={result['valid']} (expected {expected})")
    print(f"\nAll tests passed: {all_passed}")
    return all_passed


if __name__ == "__main__":
    run_test_suite()
