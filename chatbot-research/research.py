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

    # Pause for manual chat positioning before auto-typing:
    uv run python chatbot-research/research.py --pause

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

FAKE_NAME = "Test User"
FAKE_EMAIL = "test@example.com"
FAKE_ORDER = "12345"

# ---------------------------------------------------------------------------
# JavaScript: detect which chat platform a page uses
# ---------------------------------------------------------------------------
DETECT_PLATFORM_JS = """
(() => {
    const found = [];
    const globals = {
        sprinklr:   ['sprChat', '__sprChat'],
        intercom:   ['Intercom', 'intercomSettings'],
        drift:      ['drift', 'driftt'],
        zendesk:    ['zE', 'zESettings', '$zopim'],
        livechat:   ['LiveChatWidget', '__lc', 'LC_API'],
        freshchat:  ['fcWidget', 'Freshchat'],
        ada:        ['adaEmbed'],
        kustomer:   ['Kustomer'],
        hubspot:    ['HubSpotConversations'],
        salesforce: ['embedded_svc', 'liveagent'],
        genesys:    ['Genesys'],
        helpshift:  ['Helpshift'],
        liveperson: ['LivePerson', 'lpTag'],
        gladly:     ['Gladly'],
        nuance:     ['nuanceChat', 'InqRegistry'],
    };
    for (const [name, vars] of Object.entries(globals)) {
        for (const v of vars) {
            try { if (window[v]) { found.push({name, via: 'global:' + v}); break; } }
            catch(e) {}
        }
    }
    const scripts = [...document.querySelectorAll('script[src]')].map(s => s.src.toLowerCase());
    const pats = {
        sprinklr: /sprinklr/, intercom: /intercom/, drift: /drift/,
        zendesk: /zopim|zendesk.*web-widget/, livechat: /livechat/,
        freshchat: /freshchat|freshdesk/, salesforce: /service\\.force|salesforce.*chat/,
        hubspot: /hubspot.*conversations/, genesys: /genesys/,
        liveperson: /liveperson|lpcdn/, ada: /ada\\.support/,
        gladly: /gladly/, nuance: /nuance|inq\\.com/,
    };
    for (const [name, pat] of Object.entries(pats)) {
        if (scripts.some(s => pat.test(s)) && !found.some(f => f.name === name))
            found.push({name, via: 'script'});
    }
    const iframes = [...document.querySelectorAll('iframe')];
    for (const iframe of iframes) {
        const combo = ((iframe.name||'') + ' ' + (iframe.id||'') + ' ' + (iframe.src||'')).toLowerCase();
        if (/chat|widget|messenger|support|spr-|intercom|zendesk|drift|freshchat|ada|livechat/.test(combo)) {
            let pn = 'unknown-iframe';
            if (/spr-|sprinklr/.test(combo)) pn = 'sprinklr';
            else if (/intercom/.test(combo)) pn = 'intercom';
            else if (/zendesk/.test(combo)) pn = 'zendesk';
            else if (/drift/.test(combo)) pn = 'drift';
            else if (/freshchat/.test(combo)) pn = 'freshchat';
            else if (/ada/.test(combo)) pn = 'ada';
            if (!found.some(f => f.name === pn))
                found.push({name: pn, via: 'iframe', detail: combo.substring(0, 120)});
        }
    }
    return found;
})()
"""

# ---------------------------------------------------------------------------
# JavaScript: find chat-like input elements including shadow DOMs
# ---------------------------------------------------------------------------
FIND_INPUTS_JS = """
(() => {
    function scan(root, depth) {
        if (depth > 5) return [];
        const results = [];
        const els = root.querySelectorAll(
            'textarea, input[type="text"], input:not([type]), [contenteditable="true"]'
        );
        for (const el of els) {
            const rect = el.getBoundingClientRect();
            if (rect.width < 20 || rect.height < 10) continue;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const text = [
                el.placeholder || '', el.getAttribute('aria-label') || '',
                el.name || '', el.id || '', el.className || ''
            ].join(' ').toLowerCase();
            let score = 0;
            if (/message|chat|type.*here|ask|write.*here|send|reply/i.test(text)) score += 5;
            if (el.tagName === 'TEXTAREA') score += 2;
            if (rect.y > window.innerHeight * 0.5) score += 1;
            if (rect.x > window.innerWidth * 0.5) score += 1;
            if (/search|login|email|password|phone|zip|address|coupon|promo/.test(text)) score -= 10;
            if (el.type === 'search' || el.type === 'email' || el.type === 'password') score -= 10;
            results.push({
                tag: el.tagName.toLowerCase(), placeholder: el.placeholder || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                name: el.name || '', id: el.id || '',
                score, depth, x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
            });
        }
        for (const el of root.querySelectorAll('*')) {
            if (el.shadowRoot) results.push(...scan(el.shadowRoot, depth + 1));
        }
        return results;
    }
    return scan(document, 0).sort((a, b) => b.score - a.score);
})()
"""

# ---------------------------------------------------------------------------
# Platform-specific open-chat button selectors
# ---------------------------------------------------------------------------
PLATFORM_OPENERS: dict[str, list[str]] = {
    "sprinklr": [
        'div[class*="spr"] button',
        '[id*="spr"] button',
        'div[class*="sprinklr"] button',
    ],
    "intercom": [
        '.intercom-lightweight-app-launcher',
        '#intercom-container .intercom-launcher',
        '[aria-label*="intercom" i]',
    ],
    "zendesk": [
        '#launcher',
        '.zEWidget-launcher',
        'iframe#launcher',
    ],
    "drift": [
        '#drift-widget button',
        '.drift-open-chat',
        '#drift-frame-controller',
    ],
    "livechat": [
        '#chat-widget-minimized',
        '.livechat-widget-button',
    ],
    "freshchat": [
        '#fc_frame',
        '.fc-widget-open',
    ],
    "salesforce": [
        '.embeddedServiceHelpButton button',
        '.helpButtonEnabled button',
    ],
    "ada": [
        '#ada-chat-frame',
        '#ada-button-frame',
    ],
    "liveperson": [
        '[id*="LPMcontainer"] button',
        '.LPMcontainer button',
    ],
    "genesys": [
        '.cx-widget button',
        '[id*="genesys"] button',
    ],
    "nuance": [
        '#inqChatStage',
        '[class*="nuance"] button',
        '#tcChat_openChatButton',
    ],
    "gladly": [
        '#gladly-chat-button',
        '.gladly-chat-launcher',
    ],
}

# Generic open-chat selectors (when no platform detected).
GENERIC_OPENERS = [
    '[aria-label*="chat" i]:not(input):not(textarea)',
    'button:has-text("Chat")',
    'button:has-text("chat with us")',
    'button:has-text("Need help")',
    'button:has-text("Ask")',
    'a:has-text("Chat with us")',
    '#chat-button',
    '.chat-button',
    '.chat-launcher',
    '.chat-toggle',
    '[data-testid="chat-button"]',
    '[data-testid="ChatButton"]',
    'div[style*="position: fixed"][style*="bottom"][style*="right"] button',
]

# Input selectors tried inside chat context (iframe or page).
CHAT_INPUT_SELECTORS = [
    'textarea[placeholder*="message" i]',
    'textarea[placeholder*="type" i]',
    'textarea[placeholder*="ask" i]',
    'textarea[placeholder*="write" i]',
    'textarea[placeholder*="reply" i]',
    'input[placeholder*="message" i]',
    'input[placeholder*="type" i]',
    'input[placeholder*="ask" i]',
    'textarea[aria-label*="message" i]',
    'textarea[aria-label*="type" i]',
    'textarea[aria-label*="chat" i]',
    'textarea[aria-label*="reply" i]',
    'input[aria-label*="message" i]',
    'input[aria-label*="type" i]',
    'input[aria-label*="chat" i]',
    'textarea[name*="message" i]',
    'input[name*="message" i]',
    '.chat-input textarea',
    '.chat-input input',
    '#chat-input',
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

# Overlays, cookie banners, surveys, and popups to dismiss.
OVERLAY_SELECTORS = [
    'button:has-text("Accept")',
    'button:has-text("Accept All")',
    'button:has-text("Accept all")',
    'button:has-text("Got it")',
    'button:has-text("I agree")',
    'button:has-text("Agree")',
    'button:has-text("OK")',
    'button:has-text("Close")',
    'button:has-text("No thanks")',
    'button:has-text("Dismiss")',
    'button:has-text("Not now")',
    '[aria-label*="accept" i]',
    '[aria-label*="close" i][aria-label*="banner" i]',
    '[aria-label*="dismiss" i]',
    '#onetrust-accept-btn-handler',
    '#onetrust-close-btn-container button',
    '.onetrust-close-btn-handler',
    '#cookie-accept',
    '.cookie-consent-accept',
    '#truste-consent-button',
    '.trustarc-agree-btn',
    '[data-testid="close-button"]',
    '#QSIFeedbackButton-close-btn',
    '[id*="QSI"] button[aria-label*="close" i]',
    '.QSIWebResponsiveDialog-Close',
]

# Chat-related keywords for identifying chat iframes.
CHAT_IFRAME_KEYWORDS = (
    "chat", "widget", "intercom", "drift", "zendesk",
    "salesforce", "livechat", "freshchat", "spr-",
    "sprinklr", "ada", "kustomer", "helpshift",
    "messenger", "support", "liveperson", "nuance",
    "genesys", "gladly",
)


def load_targets(path: Path = TARGETS_FILE) -> dict:
    """Load the targets YAML file and return the parsed dict."""
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


def pick_prompt(config: dict, index: int, product_action: str) -> str:
    """Round-robin a prompt template from the config and fill in the action."""
    templates = config["prompts"]
    template = templates[index % len(templates)]
    return template.replace("{product_action}", product_action)


async def try_selectors(context, selectors: list[str], *, timeout: int = 3000):
    """Try a list of CSS/text selectors and return the first visible match."""
    for sel in selectors:
        try:
            locator = context.locator(sel).first
            if await locator.is_visible(timeout=timeout):
                return locator
        except Exception:
            continue
    return None


async def dismiss_overlays(page, *, passes: int = 3) -> int:
    """Dismiss cookie banners, survey popups, and overlay dialogs.

    Runs multiple passes because dismissing one overlay can reveal another.
    Returns the number of overlays dismissed.
    """
    dismissed = 0
    for _ in range(passes):
        found_any = False
        for sel in OVERLAY_SELECTORS:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=800):
                    await btn.click()
                    await page.wait_for_timeout(500)
                    dismissed += 1
                    found_any = True
                    break  # Re-start the selector list after a dismiss.
            except Exception:
                continue
        if not found_any:
            break
    return dismissed


async def trigger_lazy_widgets(page) -> None:
    """Scroll down and back up, and wait, to trigger lazy-loaded chat widgets."""
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(1000)


async def detect_platform(page) -> list[dict]:
    """Use JavaScript to detect which chat platform(s) a page uses."""
    try:
        return await page.evaluate(DETECT_PLATFORM_JS)
    except Exception as exc:
        logger.debug("Platform detection failed: %s", exc)
        return []


async def find_inputs_in_frames(page) -> list[tuple]:
    """Search all chat-related iframes for input elements.

    Returns list of (frame, locator) tuples.
    """
    results = []
    for frame in page.frames:
        name = frame.name or ""
        url = frame.url or ""
        combined = (name + " " + url).lower()
        if not any(kw in combined for kw in CHAT_IFRAME_KEYWORDS):
            continue

        logger.debug("Checking iframe: name=%r url=%s", name, url[:80])
        for sel in CHAT_INPUT_SELECTORS:
            try:
                locator = frame.locator(sel).first
                if await locator.is_visible(timeout=2000):
                    results.append((frame, locator))
                    logger.info("Found input in iframe %r: %s", name, sel)
                    break  # One input per frame is enough.
            except Exception:
                continue
    return results


async def open_chat_widget(page, platforms: list[dict], target: dict) -> bool:
    """Try to open the chat widget using platform-specific or generic selectors.

    Returns True if something was clicked.
    """
    # 1. Site-specific open selector from targets.yaml.
    hints = target.get("chat_hints") or {}
    if hints.get("open_selector"):
        try:
            btn = page.locator(hints["open_selector"]).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                logger.info("Opened chat via site-specific selector: %s",
                            hints["open_selector"])
                await page.wait_for_timeout(3000)
                return True
        except Exception as exc:
            logger.debug("Site-specific open failed: %s", exc)

    # 2. Platform-specific openers.
    for plat in platforms:
        openers = PLATFORM_OPENERS.get(plat["name"], [])
        if not openers:
            continue
        opener = await try_selectors(page, openers, timeout=2000)
        if opener:
            try:
                await opener.click()
                logger.info("Opened chat via %s-specific selector", plat["name"])
                await page.wait_for_timeout(3000)
                return True
            except Exception as exc:
                logger.debug("Platform opener click failed: %s", exc)

    # 3. Try launcher iframes (some platforms put the open button in an iframe).
    for frame in page.frames:
        name_lower = (frame.name or "").lower()
        if "launcher" in name_lower or "button" in name_lower:
            try:
                btn = frame.locator("button").first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    logger.info("Clicked launcher iframe button: %r", frame.name)
                    await page.wait_for_timeout(3000)
                    return True
            except Exception:
                continue

    # 4. Generic openers.
    opener = await try_selectors(page, GENERIC_OPENERS, timeout=2000)
    if opener:
        try:
            await opener.click()
            logger.info("Opened chat via generic selector")
            await page.wait_for_timeout(3000)
            return True
        except Exception as exc:
            logger.debug("Generic opener click failed: %s", exc)

    return False


async def find_chat_input(page, target: dict):
    """Find the chat input field, searching iframes first, then the main page.

    Returns (context, locator) or (None, None).
    """
    # 1. Site-specific input selector.
    hints = target.get("chat_hints") or {}
    if hints.get("input_selector"):
        for frame in page.frames:
            try:
                loc = frame.locator(hints["input_selector"]).first
                if await loc.is_visible(timeout=2000):
                    return frame, loc
            except Exception:
                continue
        try:
            loc = page.locator(hints["input_selector"]).first
            if await loc.is_visible(timeout=2000):
                return page, loc
        except Exception:
            pass

    # 2. Search chat-related iframes.
    frame_inputs = await find_inputs_in_frames(page)
    if frame_inputs:
        return frame_inputs[0]

    # 3. Search the main page with standard selectors.
    for sel in CHAT_INPUT_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=2000):
                # Verify it's not a search box or similar non-chat input.
                placeholder = await loc.get_attribute("placeholder") or ""
                aria = await loc.get_attribute("aria-label") or ""
                combined = (placeholder + " " + aria).lower()
                if any(kw in combined for kw in
                       ("search", "find", "look up", "zip", "email", "phone")):
                    logger.debug("Skipping non-chat input: %s", combined[:60])
                    continue
                return page, loc
        except Exception:
            continue

    # 4. JavaScript scan for unusual inputs (shadow DOMs, web components).
    try:
        js_inputs = await page.evaluate(FIND_INPUTS_JS)
        for inp in js_inputs:
            if inp["score"] <= 0:
                break
            logger.info("JS scan found candidate: score=%d tag=%s placeholder=%r",
                        inp["score"], inp["tag"], inp.get("placeholder", ""))
            sel = None
            if inp.get("id"):
                sel = f'#{inp["id"]}'
            elif inp.get("name"):
                sel = f'{inp["tag"]}[name="{inp["name"]}"]'
            elif inp.get("placeholder"):
                # Escape quotes in placeholder for CSS selector.
                ph = inp["placeholder"].replace('"', '\\"')
                sel = f'{inp["tag"]}[placeholder="{ph}"]'
            if sel:
                try:
                    loc = page.locator(sel).first
                    if await loc.is_visible(timeout=2000):
                        return page, loc
                except Exception:
                    continue
    except Exception as exc:
        logger.debug("JS input scan failed: %s", exc)

    return None, None


async def extract_response(context) -> str | None:
    """Best-effort extraction of the chatbot's last response text."""
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
        '[class*="answer"]:last-of-type',
        '[class*="reply"]:last-of-type',
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


def save_result(result: dict, name: str, timestamp: str) -> None:
    """Write a result JSON to the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}-{timestamp}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    logger.info("[%s] result saved to %s", name, path.name)


async def test_chatbot(
    page,
    name: str,
    url: str,
    prompt: str,
    target: dict,
    *,
    pause_mode: bool = False,
) -> dict:
    """Visit a chatbot, send a prompt, capture screenshots and response text."""
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    result: dict = {
        "company": name,
        "url": url,
        "prompt": prompt,
        "timestamp": timestamp,
        "response": None,
        "played_along": None,
        "chat_found": False,
        "platform": None,
        "notes": target.get("notes"),
    }

    ss_before = SCREENSHOTS_DIR / f"{name}-{timestamp}-before.png"
    ss_after = SCREENSHOTS_DIR / f"{name}-{timestamp}-after.png"
    ss_error = SCREENSHOTS_DIR / f"{name}-{timestamp}-error.png"

    try:
        # --- Phase 1: Navigate and prepare the page ---
        logger.info("[%s] navigating to %s", name, url)
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        logger.info("[%s] waiting 8s for page scripts to load...", name)
        await page.wait_for_timeout(8000)

        dismissed = await dismiss_overlays(page)
        if dismissed:
            logger.info("[%s] dismissed %d overlay(s)", name, dismissed)

        await trigger_lazy_widgets(page)
        await dismiss_overlays(page, passes=2)

        # Additional wait for widgets triggered by scroll.
        await page.wait_for_timeout(3000)

        await page.screenshot(path=str(ss_before), full_page=False)
        logger.info("[%s] before-screenshot saved", name)

        # --- Phase 2: Detect the chat platform ---
        platforms = await detect_platform(page)
        if platforms:
            primary = platforms[0]["name"]
            result["platform"] = primary
            logger.info("[%s] detected platform: %s (via %s)",
                        name, primary, platforms[0].get("via", "?"))
        else:
            logger.info("[%s] no chat platform detected", name)

        # --- Phase 3: Open the chat widget ---
        if not pause_mode:
            opened = await open_chat_widget(page, platforms, target)
            if opened:
                logger.info("[%s] chat widget opened", name)
                await page.wait_for_timeout(3000)
                await dismiss_overlays(page, passes=1)
            else:
                logger.info("[%s] could not auto-open chat — "
                            "trying input search anyway", name)
        else:
            logger.info("[%s] PAUSE MODE — manually open the chat widget, "
                        "then press Enter", name)
            print(f"\n{'=' * 60}")
            print(f"  TARGET: {name} ({url})")
            print(f"  Open the chat widget manually in the browser window.")
            print(f"  Press Enter when ready for auto-typing...")
            print(f"{'=' * 60}")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, input)
            logger.info("[%s] resuming after manual positioning", name)
            await page.wait_for_timeout(1000)

        # --- Phase 4: Find the chat input ---
        context, input_field = await find_chat_input(page, target)

        if not input_field:
            result["notes"] = (
                (result["notes"] or "") + " | Could not find chat input field"
            )
            logger.warning("[%s] no chat input found — screenshotting "
                           "and moving on", name)
            await page.screenshot(path=str(ss_error), full_page=False)
            save_result(result, name, timestamp)
            return result

        result["chat_found"] = True
        logger.info("[%s] chat input found — typing prompt", name)

        # --- Phase 5: Type the prompt and send ---
        await input_field.click()
        await page.wait_for_timeout(300)
        await input_field.fill(prompt)
        await page.wait_for_timeout(500)

        send_btn = await try_selectors(context, CHAT_SEND_SELECTORS, timeout=2000)
        if send_btn:
            await send_btn.click()
            logger.info("[%s] clicked send button", name)
        else:
            await input_field.press("Enter")
            logger.info("[%s] pressed Enter to send", name)

        # --- Phase 6: Wait for response ---
        logger.info("[%s] prompt sent — waiting up to 15s for response...",
                    name)
        await page.wait_for_timeout(15_000)

        # --- Phase 7: Capture result ---
        await page.screenshot(path=str(ss_after), full_page=False)
        logger.info("[%s] after-screenshot saved", name)

        response_text = await extract_response(context)
        if response_text:
            result["response"] = response_text
            logger.info("[%s] response captured (%d chars)",
                        name, len(response_text))
        else:
            result["notes"] = (
                (result["notes"] or "") +
                " | Could not extract response text"
            )
            logger.warning("[%s] could not extract response text "
                           "(check screenshot)", name)

    except Exception as exc:
        result["notes"] = (result["notes"] or "") + f" | Error: {exc}"
        logger.error("[%s] error: %s", name, exc)
        try:
            await page.screenshot(path=str(ss_error), full_page=False)
        except Exception:
            pass

    save_result(result, name, timestamp)
    return result


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
        lines.append(
            f"| {r['company']} | {r['prompt'][:60]}... | {resp} | {ss} |"
        )

    lines += [
        "",
        "## Refused (redirected to on-topic)\n",
        "| Company | Prompt Used | How It Refused | Screenshot |",
        "|---------|------------|----------------|------------|",
    ]
    for r in refused:
        resp = (r.get("response") or "see screenshot")[:80]
        ss = f"{r['company']}-{r['timestamp']}-after.png"
        lines.append(
            f"| {r['company']} | {r['prompt'][:60]}... | {resp} | {ss} |"
        )

    lines += [
        "",
        "## No Chat Widget Found\n",
        "| Company | URL | Platform Detected | Notes |",
        "|---------|-----|-------------------|-------|",
    ]
    for r in no_chat:
        notes = (r.get("notes") or "").strip(" |")
        platform = r.get("platform") or "none"
        lines.append(
            f"| {r['company']} | {r['url']} | {platform} | {notes} |"
        )

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
    pause_mode: bool = False,
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
    total = len(targets)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        browser_context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        for i, target in enumerate(targets):
            prompt = pick_prompt(
                {"prompts": prompts}, i, target["product_action"],
            )
            logger.info("--- [%d/%d] %s ---", i + 1, total, target["name"])

            page = await browser_context.new_page()
            try:
                result = await test_chatbot(
                    page,
                    name=target["name"],
                    url=target["url"],
                    prompt=prompt,
                    target=target,
                    pause_mode=pause_mode,
                )
                results.append(result)
            finally:
                await page.close()

            if i < total - 1:
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
        "--pause",
        action="store_true",
        help="Pause at each target for manual chat positioning "
             "before auto-typing",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Generate summary.md from existing results without "
             "running browsers",
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

    results = asyncio.run(
        run(targets, prompts, headless=args.headless, pause_mode=args.pause),
    )

    summary = generate_summary()
    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    logger.info("Summary written to %s", SUMMARY_FILE)

    chat_found = sum(1 for r in results if r.get("chat_found"))
    logger.info("Done. %d/%d targets had chat input found.",
                chat_found, len(results))


if __name__ == "__main__":
    main()
