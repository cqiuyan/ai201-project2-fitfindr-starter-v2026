"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""
import re 
import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────
def run_agent(query: str, wardrobe: dict) -> dict:
    """ 
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None."""
    
    session = new_session(query, wardrobe)

    step = "parse"
    count = 0

    try:
        while True:
            count += 1
            trace.check_iterations(count)

            # ── Step 1: parse query ──────────────────────────────────────────
            if step == "parse":

                price_match = re.search(
                    r"(?:under|below|max(?:imum)?(?: price)?(?: of)?)\s*\$?(\d+(?:\.\d+)?)",
                    session["query"],
                    re.IGNORECASE,
                )

                if price_match:
                    max_price = float(price_match.group(1))
                else:
                    max_price = None

                size_match = re.search(
                    r"\bsize\s+([A-Za-z0-9/]+)",
                    session["query"],
                    re.IGNORECASE,
                )

                if size_match:
                    size = size_match.group(1)
                else:
                    size = None

                description = re.sub(
                    r"(?:under|below|max(?:imum)?(?: price)?(?: of)?)\s*\$?\d+(?:\.\d+)?",
                    "",
                    session["query"],
                    flags=re.IGNORECASE,
                )

                description = re.sub(
                    r"\bsize\s+[A-Za-z0-9/]+",
                    "",
                    description,
                    flags=re.IGNORECASE,
                )

                description = re.sub(
                    r"\b(?:looking for|find me|find|want|need|i'm looking for|i am looking for)\b",
                    "",
                    description,
                    flags=re.IGNORECASE,
                )

                description = " ".join(description.split()).strip(" ,.-")

                session["parsed"] = {
                    "description": description,
                    "size": size,
                    "max_price": max_price,
                }

                trace.step(
                    "parse_query",
                    inputs={"query": session["query"]},
                    returned=session["parsed"],
                )

                step = "search"

            # ── Step 2: search listings through MCP ──────────────────────────
            elif step == "search":

                parsed = session["parsed"]

                session["search_results"] = call_tool(
                    "search_listings",
                    {
                        "description": parsed["description"],
                        "size": parsed["size"],
                        "max_price": parsed["max_price"],
                    },
                )

                trace.step(
                    "search_listings",
                    inputs=parsed,
                    returned=session["search_results"],
                )

                # THE BRANCH
                if not session["search_results"]:
                    session["error"] = (
                        "I couldn't find any matching listings. "
                        "Try increasing your price limit, choosing another size, "
                        "or using broader search terms."
                    )
                    return session

                session["selected_item"] = session["search_results"][0]

                step = "outfit"

            # ── Step 3: suggest outfit ───────────────────────────────────────
            elif step == "outfit":

                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"],
                    session["wardrobe"],
                )

                trace.step(
                    "suggest_outfit",
                    inputs={
                        "new_item": session["selected_item"],
                        "wardrobe": session["wardrobe"],
                    },
                    returned=session["outfit_suggestion"],
                )

                step = "fit_card"

            # ── Step 4: create fit card ──────────────────────────────────────
            elif step == "fit_card":

                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"],
                    session["selected_item"],
                )

                trace.step(
                    "create_fit_card",
                    inputs={
                        "outfit": session["outfit_suggestion"],
                        "new_item": session["selected_item"],
                    },
                    returned=session["fit_card"],
                )

                return session

    except ModelUnavailable:
        session["error"] = (
            "The model is unavailable right now. "
            "Check the API key or model configuration and try again."
        )
        return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
