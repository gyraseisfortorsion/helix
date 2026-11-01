"""Check a running backend, optionally including a real chat and event stream.

Runs with the Python standard library, including inside the backend container.
No tokens or keys are printed or written to disk.
"""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check(base: str, origin: str | None = None, chat: bool = False) -> None:
    token = ""

    def request(path, data=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(
            base.rstrip("/") + path,
            data=None if data is None else json.dumps(data).encode(),
            headers=headers,
        )
        with urlopen(req, timeout=180) as response:
            return json.load(response)

    health = request("/api/health")
    assert health["status"] == "ok", "Health check failed"
    print("PASS API health; configured providers:", health["providers"])
    if origin:
        req = Request(
            base.rstrip("/") + "/api/session",
            method="OPTIONS",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        with urlopen(req, timeout=15) as response:
            assert response.headers.get("Access-Control-Allow-Origin") == origin, "Origin not allowed"
        print("PASS frontend CORS preflight")

    session = request("/api/session", {"demo": True, "demo_source": "public"})
    token = session["token"]
    profiles = request("/api/profiles")
    assert profiles, "No public demo profiles"
    profile = next(p for p in profiles if p["name"].startswith("Alex"))
    calls = request(f"/api/profiles/{profile['id']}/variants")
    assert calls, "Public DNA calls missing"
    wearable = request(f"/api/profiles/{profile['id']}/wearables")
    assert wearable["record_count"] > 0 and wearable["metrics"], "Wearable measurements missing"
    assert "samples" in request(f"/api/profiles/{profile['id']}/methylation")
    print(f"PASS public session, {len(profiles)} profiles, DNA, wearables and optional methylation")

    if chat:
        queued = request(
            "/api/messages",
            {"profile_id": profile["id"], "question": "Could my knee pain be genetic?"},
        )
        req = Request(
            base.rstrip("/") + f"/api/jobs/{queued['job_id']}/events",
            headers={"Authorization": "Bearer " + token, "Accept": "text/event-stream"},
        )
        with urlopen(req, timeout=180) as response:
            assert response.headers.get_content_type() == "text/event-stream", "Not an event stream"
            events = sum(1 for line in response if line.startswith(b"data: "))
        result = request(f"/api/jobs/{queued['job_id']}")
        assert result["status"] == "completed", "Chat failed; inspect backend logs"
        assert events > 0, "No streamed investigation events"
        assert result["result"]["answer"]["claims"], "No supported claims"
        print("PASS queued chat, worker, event stream and saved answer:", result["result"]["answer"]["mode"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?", default="http://127.0.0.1:8000")
    parser.add_argument("--origin", help="Exact browser frontend origin to check against CORS")
    parser.add_argument(
        "--chat", action="store_true", help="Also run a chat; uses provider credits if configured"
    )
    args = parser.parse_args()
    try:
        check(args.base, args.origin, args.chat)
    except (HTTPError, URLError, TimeoutError, AssertionError, KeyError, StopIteration) as error:
        # Error bodies and URLs may contain external input. Never dump auth headers.
        print("FAIL", type(error).__name__, str(error)[:300], file=sys.stderr)
        sys.exit(1)
