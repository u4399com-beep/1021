"""Browser Use client wrapper — Tier-2 LLM-driven browser automation.

Browser Use is an LLM-driven browser automation library: given a URL and a
natural-language task ("return the full HTML"), an LLM guides a real browser
to interact with the page and extract the answer. It is most useful when:

  - The page requires complex interaction (login, click-through, scroll)
  - Other tiers fail because of anti-bot
  - You need flexibility over speed

The cost per call is non-trivial (LLM tokens + browser session), so we
only invoke this tier when Tier-1 (Firecrawl) and Tier-0 (httpx) have failed.
"""

import asyncio
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """Browser Use needs an OpenAI-compatible LLM key to drive the agent."""
    return bool(settings.CRAWLER.get("BROWSER_USE_OPENAI_API_KEY", ""))


def _ensure_llm():
    """Lazily build an LLM driver; raise with a helpful message if deps missing."""
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "langchain-openai is not installed. "
            "Run `pip install browser-use langchain-openai` to enable the Browser Use tier."
        ) from e

    api_key = settings.CRAWLER.get("BROWSER_USE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("BROWSER_USE_OPENAI_API_KEY not configured")

    os.environ.setdefault("OPENAI_API_KEY", api_key)
    model = settings.CRAWLER.get("BROWSER_USE_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0)


async def _scrape_async(url: str, *, task_hint: str = "") -> str:
    try:
        from browser_use import Agent  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "browser-use is not installed. "
            "Run `pip install browser-use` to enable the Browser Use tier."
        ) from e

    llm = _ensure_llm()
    task = (
        f"Navigate to {url}. " + (task_hint + " " if task_hint else "") +
        "Wait for the page to fully render (including dynamic content), "
        "then return the complete HTML of the body element."
    )
    agent = Agent(task=task, llm=llm)
    result = await agent.run()
    # AgentResult may have .extracted_content or .history
    extracted = getattr(result, "extracted_content", None) or ""
    if isinstance(extracted, list):
        extracted = "\n".join(str(x) for x in extracted)
    if not extracted:
        # Fallback: try to read the final history's last page HTML
        history = getattr(result, "history", [])
        if history:
            last = history[-1]
            extracted = getattr(last, "html", "") or str(last)
    if not extracted:
        raise RuntimeError(f"browser-use: empty response for {url}")
    return str(extracted)


def scrape_html(url: str, *, task_hint: str = "") -> str:
    """Synchronous wrapper around the async scrape."""
    # Use a fresh event loop to avoid clashing with Celery's loop
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_scrape_async(url, task_hint=task_hint))
    finally:
        loop.close()
