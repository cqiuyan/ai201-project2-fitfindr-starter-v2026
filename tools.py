"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""
import re
import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings

# helper functions 
_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "under", "over", "in", "of"
}


def _keywords(text: str) -> set[str]:
    """Lowercase words worth matching on, stopwords removed."""
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _size_tokens(size: str) -> set[str]:
    """Split a size such as S/M into separate normalized size tokens."""
    cleaned = re.sub(r"\([^)]*\)", " ", size or "")  # drop parentheticals
    parts = [p.strip().upper() for p in cleaned.split("/")]
    return {p for p in parts if p}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Match sizes case-insensitively using complete size tokens.
    Examples:
        M matches S/M
        S does not match US 9
        L does not match XL
    """
    if not wanted:
        return True

    listing_tokens = _size_tokens(listing_size)

    if any(token.startswith("ONE SIZE") for token in listing_tokens):
        return True

    return bool(_size_tokens(wanted) & listing_tokens) 


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    # TODO: replace this with your implementation
    listings = load_listings()
    query_words = _keywords(description)

    scored_results = []

    for listing in listings:

        # Filter by price
        if max_price is not None and listing["price"] > max_price:
            continue

        # Filter by size
        if size is not None:
            listing_size = listing.get("size", "")

            if not _size_matches(size, listing_size):
                continue

        # Build text to search
        searchable_text = " ".join([
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", [])),
            " ".join(listing.get("colors", [])),
            listing.get("brand") or "",
            listing.get("platform", ""),
        ])

        listing_words = _keywords(searchable_text)

        # Score based on number of matching keywords
        score = len(query_words & listing_words)

        # Drop listings with no matching keywords
        if score == 0:
            continue

        scored_results.append((score, listing))

    # Highest score first
    scored_results.sort(key=lambda pair: pair[0], reverse=True)

    # Return only the listing dictionaries
    return [
        listing
        for score, listing in scored_results[:config.SEARCH_RESULT_LIMIT]
    ]



# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    # TODO: replace this with your implementation

    wardrobe_items = wardrobe.get("items", [])

    item_description = (
        f"Title: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', '')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
    )

    # Empty wardrobe
    if not wardrobe_items:
        prompt = f"""
The user is considering this thrifted item: {item_description}

The user's wardrobe is empty.

Suggest one or two general ways to style this item.
Be specific and practical.
Do not claim the user already owns any particular clothing pieces.
Keep the response concise.
"""

        return generate(prompt).strip()

    # Format the user's wardrobe
    wardrobe_lines = []

    for item in wardrobe_items:
        wardrobe_lines.append(str(item))

    wardrobe_text = "\n".join(wardrobe_lines)

    prompt = f"""
The user is considering this thrifted item: {item_description}
Here are the items in the user's wardrobe: {wardrobe_text}

Suggest one or two outfits using the thrifted item together with specific
pieces the user already owns.

Name the wardrobe pieces you use.
Keep the suggestions concise, practical, and specific.
"""

    return generate(prompt).strip()



# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    # TODO: replace this with your implementation
    # Guard against empty outfit
    if not outfit or not outfit.strip():
        return (
            "I couldn't create a fit card because there wasn't an outfit "
            "suggestion to work from."
        )

    title = new_item.get("title", "thrifted find")
    price = new_item.get("price", 0)
    platform = new_item.get("platform", "the listing platform")
    colors = ", ".join(new_item.get("colors", []))
    style_tags = ", ".join(new_item.get("style_tags", []))

    prompt = f"""
Write a short social-media-style caption about this thrifted find.

Item: {title}
Price: ${price:.2f}
Platform: {platform}
Colors: {colors}
Style tags: {style_tags}

Outfit suggestion:
{outfit}

Requirements:
- Write 2 to 4 sentences.
- Make it sound like a real person posting about a thrift find.
- Mention the item once.
- Mention the price once.
- Mention the platform once.
- Be specific about the outfit's vibe.
- Do not make it sound like a product description.
"""

    return generate(prompt).strip()

