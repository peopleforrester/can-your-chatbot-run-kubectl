# ABOUTME: Playwright-based research script that visits public chatbot widgets with lighthearted prompts.
# ABOUTME: Captures before/after screenshots and response text for the KubeCon talk submission.

"""Chatbot Dance Moves Research — screenshot capture for the CFP.

Usage:
    # Run all targets (one prompt each, round-robin):
    uv run python chatbot-research/research.py

    # Run a single target by name:
    uv run python chatbot-research/research.py --target chipotle

    # Run with headless browser (fallback when no display):
    uv run python chatbot-research/research.py --headless

    # Generate summary only (from existing results):
    uv run python chatbot-research/research.py --summary-only

Rules:
    - ONE prompt per chatbot. No repeat visits.
    - No prompt injection. No adversarial behavior.
    - Skip anything that requires login.
    - Use obviously fake data if asked for PII.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger("chatbot-research")

SCRIPT_DIR = Path(__file__).resolve().parent
TARGETS_FILE = SCRIPT_DIR / "targets.yaml"
SCREENSHOTS_DIR = SCRIPT_DIR / "screenshots"
RESULTS_DIR = SCRIPT_DIR / "results"
SUMMARY_FILE = SCRIPT_DIR / "summary.md"

# Fake PII for chatbots that ask before connecting to an agent.
FAKE_NAME = "Test User"
FAKE_EMAIL = "test@example.com"
FAKE_ORDER = "12345"

# Common selectors for chat widgets across sites. The script tries these
# in order; the first match wins. Site-specific overrides go in targets.yaml.
CHAT_OPEN_SELECTORS = [
    # Aria-based
    '[aria-label*="chat" i]',
    '[aria-label*="Chat" i]',
    '[aria-label*="help" i]',
    '[aria-label*="assistant" i]',
    '[aria-label*="support" i]',
    # Common class/id patterns
    "#chat-button",
    "#chat-widget",
    ".chat-button",
    ".chat-launcher",
    ".chat-toggle",
    # Text-based
    'button:has-text("Chat")',
    'button:has-text("chat")',
    'button:has-text("Need help")',
    'button:has-text("Ask")',
    'a:has-text("Chat with us")',
    # Widget-specific (Intercom, Drift, Zendesk, etc.)
    "#intercom-container iframe",
    ".intercom-lightweight-app-launcher",
    "#drift-widget",
    ".drift-open-chat",
    '[data-testid="chat-button"]',
    '[data-testid="ChatButton"]',
    "#launcher",  # Zendesk
    ".zEWidget-launcher",
    # Generic floating button bottom-right
    'div[style*="position: fixed"][style*="bottom"][style*="right"] button',
]

CHAT_INPUT_SELECTORS = [
    '[aria-label*="message" i]',
    '[aria-label*="type" i]',
    '[aria-label*="chat" i]',
    '[placeholder*="message" i]',
    '[placeholder*="type" i]',
    '[placeholder*="ask" i]',
    'textarea[name*="message" i]',
    'input[name*="message" i]',
    ".chat-input textarea",
    ".chat-input input",
    "#chat-input",
    '[data-testid="chat-input"]',
    '[contenteditable="true"]',
]

CHAT_SEND_SELECTORS = [
    '[aria-label*="send" i]',
    'button:has-text("Send")',
    'button[type="submit"]',
    '.chat-send',
    '[data-testid="send-button"]',
]


def load_targets(path: Path = TARGETS_FILE) -> dict:
    """Load the targets YAML file and return the parsed dict."""
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


def pick_prompt(config: dict, index: int, product_action: str) -> str:
    """Round-robin a prompt template from the config and fill in the action."""
    templates = config["prompts"]
    template = templates[index % len(templates)]
    return template.replace("{product_action}", product_action)


async def try_selectors(page, selectors: list[str], *, timeout: int = 3000):
    """Try a list of CSS/text selectors and return the first visible match."""
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            if await locator.is_visible(timeout=timeout):
                return locator
        except Exception:
            continue
    return None


async def check_for_iframe_chat(page):
    """Some sites embed the chat in an iframe. Try to find and enter it."""
    for frame in page.frames:
        name = frame.name or ""
        url = frame.url or ""
        if any(kw in name.lower() or kw in url.lower()
               for kw in ("chat", "widget", "intercom", "drift", "zendesk",
                          "salesforce", "livechat", "freshchat")):
            return frame
    return None


async def test_chatbot(
    page,
    name: str,
    url: str,
    prompt: str,
    notes: str | None = None,
    *,
    headless: bool = False,
) -> dict:
    """Visit a chatbot, send a prompt, capture screenshots and response text.

    Returns a result dict written to RESULTS_DIR.
    """
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    result: dict = {
        "company": name,
        "url": url,
        "prompt": prompt,
        "timestamp": timestamp,
        "response": None,
        "played_along": None,
        "chat_found": False,
        "notes": notes,
    }

    ss_before = SCREENSHOTS_DIR / f"{name}-{timestamp}-before.png"
    ss_after = SCREENSHOTS_DIR / f"{name}-{timestamp}-after.png"
    ss_error = SCREENSHOTS_DIR / f"{name}-{timestamp}-error.png"

    try:
        logger.info("[%s] navigating to %s", name, url)
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        # Let deferred chat widgets and consent banners load.
        await page.wait_for_timeout(5000)

        # Dismiss common cookie/consent banners that block interaction.
        for consent_sel in (
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Got it")',
            'button:has-text("I agree")',
            '[aria-label*="accept" i]',
            "#onetrust-accept-btn-handler",
        ):
            try:
                btn = page.locator(consent_sel).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await page.wait_for_timeout(500)
                    break
            except Exception:
                continue

        await page.screenshot(path=str(ss_before), full_page=False)
        logger.info("[%s] before-screenshot saved", name)

        # --- Find the chat widget ---
        chat_opened = False

        # Step 1: try clicking an open-chat button on the main page.
        opener = await try_selectors(page, CHAT_OPEN_SELECTORS, timeout=2000)
        if opener:
            logger.info("[%s] found chat open button", name)
            await opener.click()
            await page.wait_for_timeout(3000)
            chat_opened = True

        # Step 2: check for iframe-embedded chat.
        chat_frame = await check_for_iframe_chat(page)
        context = chat_frame if chat_frame else page

        # Step 3: find the input field.
        input_field = await try_selectors(context, CHAT_INPUT_SELECTORS, timeout=5000)
        if not input_field and chat_frame:
            # Retry on main page if iframe had no input.
            input_field = await try_selectors(page, CHAT_INPUT_SELECTORS, timeout=3000)
            context = page

        if not input_field:
            result["notes"] = (result["notes"] or "") + " | Could not find chat input field"
            logger.warning("[%s] no chat input found — screenshotting and moving on", name)
            await page.screenshot(path=str(ss_error), full_page=False)
            _save_result(result, name, timestamp)
            return result

        result["chat_found"] = True
        logger.info("[%s] chat input found — typing prompt", name)

        # Step 4: type the prompt and send.
        await input_field.click()
        await input_field.fill(prompt)
        await page.wait_for_timeout(500)

        send_btn = await try_selectors(context, CHAT_SEND_SELECTORS, timeout=2000)
        if send_btn:
            await send_btn.click()
        else:
            # Fallback: press Enter.
            await input_field.press("Enter")

        # Step 5: wait for a response (generous timeout — some bots are slow).
        logger.info("[%s] prompt sent — waiting up to 15s for response", name)
        await page.wait_for_timeout(15_000)

        # Step 6: screenshot the chat with the response visible.
        await page.screenshot(path=str(ss_after), full_page=False)
        logger.info("[%s] after-screenshot saved", name)

        # Step 7: try to extract response text.
        response_text = await _extract_response(context)
        if response_text:
            result["response"] = response_text
            logger.info("[%s] response captured (%d chars)", name, len(response_text))
        else:
            result["notes"] = (result["notes"] or "") + " | Could not extract response text"
            logger.warning("[%s] could not extract response text", name)

    except Exception as exc:
        result["notes"] = (result["notes"] or "") + f" | Error: {exc}"
        logger.error("[%s] error: %s", name, exc)
        try:
            await page.screenshot(path=str(ss_error), full_page=False)
        except Exception:
            pass

    _save_result(result, name, timestamp)
    return result


async def _extract_response(context) -> str | None:
    """Best-effort extraction of the chatbot's last response text."""
    # Common response container selectors.
    for sel in (
        ".chat-message:last-child",
        ".message-bubble:last-child",
        '[data-testid="bot-message"]:last-child',
        ".bot-response:last-child",
        ".agent-message:last-child",
        ".chat-response:last-child",
        '[class*="botMessage"]:last-of-type',
        '[class*="agent"]:last-of-type',
        '[class*="response"]:last-of-type',
    ):
        try:
            el = context.locator(sel).last
            if await el.is_visible(timeout=1000):
                text = await el.inner_text(timeout=2000)
                if text and len(text.strip()) > 10:
                    return text.strip()
        except Exception:
            continue
    return None


def _save_result(result: dict, name: str, timestamp: str) -> None:
    """Write a result JSON to the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}-{timestamp}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    logger.info("[%s] result saved to %s", name, path.name)


def generate_summary() -> str:
    """Read all result JSONs and produce a markdown summary."""
    results: list[dict] = []
    for p in sorted(RESULTS_DIR.glob("*.json")):
        results.append(json.loads(p.read_text(encoding="utf-8")))

    played_along: list[dict] = []
    refused: list[dict] = []
    no_chat: list[dict] = []

    for r in results:
        if not r.get("chat_found"):
            no_chat.append(r)
        elif r.get("played_along") is True:
            played_along.append(r)
        elif r.get("played_along") is False:
            refused.append(r)
        else:
            # Unclassified — put in played_along bucket with a note.
            played_along.append(r)

    lines = [
        "# Chatbot Dance Moves Research — Results\n",
        f"*Generated {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n",
        "",
        "## Played Along (off-topic response given)\n",
        "| Company | Prompt Used | Response Summary | Screenshot |",
        "|---------|------------|------------------|------------|",
    ]
    for r in played_along:
        resp = (r.get("response") or "see screenshot")[:80]
        ss = f"{r['company']}-{r['timestamp']}-after.png"
        lines.append(f"| {r['company']} | {r['prompt'][:60]}... | {resp} | {ss} |")

    lines += [
        "",
        "## Refused (redirected to on-topic)\n",
        "| Company | Prompt Used | How It Refused | Screenshot |",
        "|---------|------------|----------------|------------|",
    ]
    for r in refused:
        resp = (r.get("response") or "see screenshot")[:80]
        ss = f"{r['company']}-{r['timestamp']}-after.png"
        lines.append(f"| {r['company']} | {r['prompt'][:60]}... | {resp} | {ss} |")

    lines += [
        "",
        "## No Chat Widget Found\n",
        "| Company | URL | Notes |",
        "|---------|-----|-------|",
    ]
    for r in no_chat:
        notes = (r.get("notes") or "").strip(" |")
        lines.append(f"| {r['company']} | {r['url']} | {notes} |")

    lines += [
        "",
        "## Best Screenshots for Talk\n",
        "*Review the `screenshots/` directory and fill in manually:*\n",
        "1. [company] — [why this screenshot is gold]",
        "2. ...",
        "",
    ]

    return "\n".join(lines)


async def run(
    targets: list[dict],
    prompts: list[str],
    *,
    headless: bool = False,
) -> list[dict]:
    """Run the research against a list of targets."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error(
            "playwright is not installed. Run: uv add --dev playwright && "
            "uv run playwright install chromium"
        )
        sys.exit(1)

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        browser_context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )

        for i, target in enumerate(targets):
            prompt = pick_prompt(
                {"prompts": prompts},
                i,
                target["product_action"],
            )
            page = await browser_context.new_page()
            try:
                result = await test_chatbot(
                    page,
                    name=target["name"],
                    url=target["url"],
                    prompt=prompt,
                    notes=target.get("notes"),
                    headless=headless,
                )
                results.append(result)
            finally:
                await page.close()

            # Manually paced — 5s between targets.
            if i < len(targets) - 1:
                logger.info("--- pausing 5s before next target ---")
                await asyncio.sleep(5)

        await browser.close()

    return results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Chatbot Dance Moves Research — screenshot capture",
    )
    parser.add_argument(
        "--target",
        help="Run only this target (by name from targets.yaml)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (some chatbots detect this)",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Generate summary.md from existing results without running browsers",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.summary_only:
        summary = generate_summary()
        SUMMARY_FILE.write_text(summary, encoding="utf-8")
        logger.info("Summary written to %s", SUMMARY_FILE)
        return

    config = load_targets()
    targets = config["targets"]
    prompts = config["prompts"]

    if args.target:
        targets = [t for t in targets if t["name"] == args.target]
        if not targets:
            logger.error("Target %r not found in targets.yaml", args.target)
            sys.exit(1)

    results = asyncio.run(run(targets, prompts, headless=args.headless))

    # Generate summary after all runs.
    summary = generate_summary()
    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    logger.info("Summary written to %s", SUMMARY_FILE)
    logger.info("Done. %d targets attempted.", len(results))


if __name__ == "__main__":
    main()
