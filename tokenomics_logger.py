from bedrock_client import invoke_claude

INPUT_PRICE_PER_M = 3.00    # USD per 1M input tokens. VERIFY on the Bedrock pricing page.
OUTPUT_PRICE_PER_M = 15.00  # USD per 1M output tokens. VERIFY on the Bedrock pricing page.

CALL_LOG = []


def cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * INPUT_PRICE_PER_M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_M


def logged_invoke(component: str, prompt: str, max_tokens: int = 500) -> dict:
    """Calls Claude and logs input tokens, output tokens and USD cost under a component name."""
    result = invoke_claude(prompt, max_tokens=max_tokens)
    cost = cost_usd(result["input_tokens"], result["output_tokens"])
    CALL_LOG.append({"component": component, "input_tokens": result["input_tokens"],
                     "output_tokens": result["output_tokens"], "cost_usd": cost})
    print(f"[TOKENS] component={component} input={result['input_tokens']} "
          f"output={result['output_tokens']} cost_usd={cost:.6f}")
    result["cost_usd"] = cost
    return result


def merge_usage(calls: list) -> dict:
    return {
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cost_usd": sum(c["cost_usd"] for c in calls),
    }


def summarize() -> None:
    by_component = {}
    for c in CALL_LOG:
        agg = by_component.setdefault(c["component"], {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        agg["calls"] += 1
        agg["in"] += c["input_tokens"]
        agg["out"] += c["output_tokens"]
        agg["cost"] += c["cost_usd"]
    print("\n" + "=" * 70)
    print(f"{'component':<28}{'calls':>6}{'in_tok':>10}{'out_tok':>10}{'cost_usd':>12}")
    for name, a in sorted(by_component.items(), key=lambda kv: -(kv[1]['in'] + kv[1]['out'])):
        print(f"{name:<28}{a['calls']:>6}{a['in']:>10}{a['out']:>10}{a['cost']:>12.6f}")
    total = sum(a["cost"] for a in by_component.values())
    print(f"\nTOTAL COST (USD): {total:.6f}")
    if by_component:
        top = max(by_component.items(), key=lambda kv: kv[1]["in"] + kv[1]["out"])[0]
        print(f"Most tokens consumed by: {top}")
