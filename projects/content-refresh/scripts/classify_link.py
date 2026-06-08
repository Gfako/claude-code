#!/usr/bin/env python3
"""
Map a (URL, HTTP-status) pair to a finding severity for the link extractor.

Rules (corrected from the original):
  - 2xx                       → drop (link is fine; doesn't need to be a finding)
  - 3xx                       → likely (verify redirect destination)
  - 401                       → likely (auth-wall / paywall)
  - 403, 405, 999             → unconfirmed (almost always bot-blocking,
                                regardless of which domain). The earlier
                                version only treated these as bot-blocked
                                for a hard-coded allowlist; that produced
                                false "Link error" findings.
  - 404                       → confirmed (real dead link)
  - other 4xx, 5xx, "000"     → likely (could be transient/network issue)
  - "&amp;" in URL with 400   → unconfirmed (HTML-entity scrape artifact;
                                real rendered link probably works)
  - everything else / "?"     → unconfirmed

Returns a dict {severity, title, suggested_fix} ready to drop into a finding.

Standalone usage:
  echo '{"url":"...","code":"403"}' | python3 classify_link.py
"""

import json
import sys


# Helper sets of domains we know need a "this is bot-blocking, not broken"
# explanation in the suggested_fix message — so the reviewer doesn't waste
# time. Not used to *filter* severity; just to enrich the wording.
_BOT_BLOCKING_HINT_DOMAINS = {
    "linkedin.com", "www.linkedin.com",
    "g2.com", "www.g2.com",
    "twitter.com", "x.com",
    "claude.ai", "chatgpt.com", "gamma.app",
    "www.weforum.org", "www.bloomberg.com", "www.forbes.com",
    "www.gartner.com", "www.salesforce.com",
    "www.sciencedirect.com", "aibusiness.com",
    "omdia.tech.informa.com", "www.grandviewresearch.com",
    "www.wsj.com",
}


def _domain(url: str) -> str:
    return url.split("//", 1)[-1].split("/", 1)[0].lower()


def classify(url: str, code: str) -> dict:
    code = (code or "").strip()
    domain = _domain(url)
    bot_hint = domain in _BOT_BLOCKING_HINT_DOMAINS

    if "&amp;" in url and code == "400":
        return {
            "severity": "unconfirmed",
            "title": "Possible HTML-entity artifact in link",
            "suggested_fix": (
                "Link returns 400, but the URL contains `&amp;` (HTML-encoded "
                "ampersand) — likely a Firecrawl scrape artifact. The actual "
                "rendered link in the browser is almost certainly fine. "
                "Manual spot-check recommended."
            ),
        }

    if code.startswith("2"):
        return {"severity": "drop", "title": "Link OK", "suggested_fix": f"HEAD returned {code}. No action."}

    if code.startswith("3"):
        # 301/302/etc — link still works for users; author may have linked to
        # a URL that's been redirected for a long time. Don't flag.
        return {"severity": "drop", "title": f"Link redirects ({code}) — OK", "suggested_fix": f"Returned {code}. Redirect resolves; no action."}

    if code in ("403", "405", "999"):
        if bot_hint:
            note = f"{domain} blocks automated checks (returned {code}). Manual spot-check in a browser if you want to be sure."
        else:
            note = (
                f"Link returned {code} to an automated HEAD check. {code} usually means the "
                "site is bot-blocking, not that the link is broken. Spot-check in a browser to confirm."
            )
        return {"severity": "unconfirmed", "title": f"Link blocks bots ({code})", "suggested_fix": note}

    if code == "401":
        return {
            "severity": "likely",
            "title": "Link requires auth (401)",
            "suggested_fix": "Link returned 401 — auth-required or paywalled. May be intentional, but worth verifying.",
        }

    if code == "404":
        return {
            "severity": "confirmed",
            "title": "Dead link (404)",
            "suggested_fix": "Link returns 404. Remove or replace.",
        }

    if code == "000":
        # Connection refused / DNS failure / unreachable — effectively dead
        # for users, even if it could theoretically be transient. Escalating
        # to confirmed so it shows red and gets attention.
        return {
            "severity": "confirmed",
            "title": "Dead link (unreachable)",
            "suggested_fix": (
                "Link is unreachable (no HTTP response — DNS failure, refused "
                "connection, or site is down). Remove or replace."
            ),
        }

    if code.startswith(("4", "5")):
        return {
            "severity": "likely",
            "title": f"Link error ({code})",
            "suggested_fix": (
                f"Link returned {code}. Could be a transient server issue or genuine "
                "breakage — verify; remove if persistently broken."
            ),
        }

    return {
        "severity": "unconfirmed",
        "title": f"Link check inconclusive ({code or 'no response'})",
        "suggested_fix": "Couldn't classify the response. Manual check recommended.",
    }


def main():
    payload = json.loads(sys.stdin.read())
    out = classify(payload["url"], payload.get("code", ""))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
