from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rercie"))
import rercie_core as app

bundle = (ROOT / "community_profiles.js").read_text(encoding="utf-8")
assert len(bundle.encode("utf-8")) <= app.MAX_COMMUNITY_PROFILE_BYTES
original_request = app._request_text
app._request_text = lambda _url, **_kwargs: bundle
try:
    exact = app.fetch_public_community_profile("St. Paul town", "Virginia")
    alias = app.fetch_public_community_profile("St. Paul", "Virginia")
    other_state = app.fetch_public_community_profile("St. Paul", "Oregon")
finally:
    app._request_text = original_request

assert exact.get("geoid") == "5169936", exact
assert alias.get("geoid") == "5169936", alias
assert other_state.get("geoid") != "5169936", other_state
print("PASS: the shipped St. Paul profile resolves by exact name and town alias.")
