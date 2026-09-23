"""
05_ai_variance_commentary.py
----------------------------
A small AI agent that drafts month-end / year-end variance commentary for the
controllers, with the controls a finance team needs before trusting it.

Pipeline
    1. FACTS    Pull verified figures from case_results.json (the single source of truth).
    2. DRAFT    Send only those facts to an LLM with strict writing rules.
                No API key? A rule-based writer produces the same structure.
    3. CHECK    Every number in the draft is matched back to the facts.
                Any number that cannot be traced is flagged for the controller.
    4. REVIEW   A controller edits and signs off. The agent never publishes on its own.

Run:
    python 05_ai_variance_commentary.py            # rule-based draft
    ANTHROPIC_API_KEY=... python 05_ai_variance_commentary.py --llm
Output: ../docs/variance_commentary_draft.md
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
res = json.loads((ROOT / "data" / "case_results.json").read_text())

# ------------------------------------------------------------------ 1. facts
p24, p25 = res["pnl"]["2024"], res["pnl"]["2025"]
bridge = {b["label"]: b["value"] for b in res["bridge"]}
contracts = {c["contract"]: c for c in res["price_by_contract"]}
cts = res["cts_findings"]
en = res["energy"]
facts = {
    "sales_2024": p24["net_sales"], "sales_2025": p25["net_sales"],
    "ebitda_2024": p24["ebitda"], "ebitda_2025": p25["ebitda"],
    "margin_2024": round(p24["ebitda_margin"] * 100, 1),
    "margin_2025": round(p25["ebitda_margin"] * 100, 1),
    "ebitda_change": round(p25["ebitda"] - p24["ebitda"], 2),
    "sales_growth_pct": round((p25["net_sales"] / p24["net_sales"] - 1) * 100, 1),
    "bridge": bridge,
    "fixed_contract_price_pct": contracts["Fixed annual"]["price_change_pct"],
    "fixed_contract_effect": contracts["Fixed annual"]["effect"],
    "indexed_price_pct": contracts["Indexed"]["price_change_pct"],
    "negative_ebitda_accounts": cts["negative_ebitda_count"],
    "negative_ebitda_value": cts["negative_ebitda_value"],
    "energy_alert_week": en["alert_week_p3"],
    "energy_excess_cost": en["excess_cost_2025"],
}

SYSTEM_PROMPT = """You are a controlling assistant drafting variance commentary for a
business unit leadership team. Rules:
- Use ONLY numbers present in the FACTS JSON. Never compute new figures except
  simple sums or differences you state explicitly.
- EUR millions with one decimal, percentages with one decimal.
- Structure: headline (one sentence), what drove the change (max 5 bullets,
  largest first), what is controllable, recommended actions, open questions.
- Separate market-driven effects (fibre, energy prices, FX) from controllable ones.
- If a fact is missing, write "to be confirmed" instead of guessing.
- Plain business English, no hype, under 220 words."""


# ------------------------------------------------------------------ 2. draft
def rule_based_draft(f: dict) -> str:
    b = f["bridge"]
    drivers = sorted(b.items(), key=lambda kv: abs(kv[1]), reverse=True)
    market = b["Fibre cost"] + b["Energy cost"] + b["FX (SEK)"]
    lines = [
        f"**Headline.** Net sales grew {f['sales_growth_pct']:.1f}% to EUR {f['sales_2025']:.1f} m, "
        f"but EBITDA fell EUR {abs(f['ebitda_change']):.1f} m to EUR {f['ebitda_2025']:.1f} m "
        f"(margin {f['margin_2024']:.1f}% to {f['margin_2025']:.1f}%).",
        "",
        "**Main drivers (EUR m).**",
    ]
    for k, v in drivers[:5]:
        lines.append(f"- {k}: {v:+.1f}")
    lines += [
        "",
        f"**Market vs controllable.** Fibre, energy prices and the weaker SEK explain "
        f"EUR {abs(market):.1f} m of the decline together. The controllable part sits in pricing: fixed annual "
        f"contracts moved {f['fixed_contract_price_pct']:.1f}% (EUR {f['fixed_contract_effect']:.1f} m) "
        f"while indexed contracts moved {f['indexed_price_pct']:+.1f}%.",
        f"{f['negative_ebitda_accounts']} accounts are EBITDA-negative after cost-to-serve "
        f"(EUR {f['negative_ebitda_value']:.1f} m).",
        "",
        "**Recommended actions.** Index clauses at contract renewal; order and delivery rules "
        "for loss-making accounts; fix the energy drift at Sweden Central, flagged by the weekly "
        f"rule in the week of {f['energy_alert_week']} (EUR {f['energy_excess_cost']:.2f} m excess in the year).",
        "",
        "**Open questions.** Renewal calendar of fixed contracts: to be confirmed. "
        "Root cause of the energy drift: to be confirmed by maintenance.",
    ]
    return "\n".join(lines)


def llm_draft(f: dict) -> str:
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "FACTS:\n" + json.dumps(f, indent=1)}],
    )
    return msg.content[0].text


# ------------------------------------------------------------------ 3. check
def allowed_numbers(f) -> set:
    vals = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (int, float)):
            for d in (0, 1, 2):
                vals.add(round(abs(x), d))
        elif isinstance(x, str):
            for n in re.findall(r"\d+(?:\.\d+)?", x):
                vals.add(float(n))
    walk(f)
    b = f["bridge"]
    vals.add(round(abs(b["Fibre cost"] + b["Energy cost"] + b["FX (SEK)"]), 1))  # stated sum
    return vals


def number_check(text: str, f: dict) -> list:
    ok = allowed_numbers(f)
    flagged = []
    for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", text):
        x = float(n)
        if x in ok or round(x, 1) in ok or x < 10 and x == int(x):  # small integers = list counts
            continue
        flagged.append(n)
    return flagged


if __name__ == "__main__":
    use_llm = "--llm" in sys.argv and os.environ.get("ANTHROPIC_API_KEY")
    draft = llm_draft(facts) if use_llm else rule_based_draft(facts)
    issues = number_check(draft, facts)
    status = "PASSED: every number traces to the facts" if not issues else \
        f"REVIEW: {len(issues)} number(s) not found in facts: {', '.join(issues)}"
    out = (f"# Variance commentary draft, FY2025 vs FY2024\n\n"
           f"_Source: {'LLM agent' if use_llm else 'rule-based fallback'}. "
           f"Number check {status}. Controller sign-off required._\n\n{draft}\n")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "variance_commentary_draft.md").write_text(out)
    print(out)
