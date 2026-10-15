#!/usr/bin/env python3
"""Bootstrap the SoftMobile sales workflow using Chatwoot's existing public API.

No changes are made without --apply. No third-party dependencies are needed.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib import error, parse, request

RESOURCE_CONFIG = (
    ("labels", "label", ("title",)),
    ("canned_responses", "canned_response", ("short_code",)),
    ("custom_attribute_definitions", "custom_attribute_definition", ("attribute_key", "attribute_model")),
    ("automation_rules", None, ("name",)),
)


def load_manifest(path):
    with Path(path).open(encoding="utf-8") as file:
        manifest = json.load(file)
    for endpoint, _wrapper, keys in RESOURCE_CONFIG:
        rows = manifest.get(endpoint)
        if not isinstance(rows, list):
            raise ValueError(f"{endpoint} must be a list")
        identifiers = set()
        for item in rows:
            if not isinstance(item, dict) or any(not isinstance(item.get(key), str) or not item[key] for key in keys):
                raise ValueError(f"{endpoint}: missing or invalid identifier {keys}")
            identifier = tuple(item[key] for key in keys)
            if identifier in identifiers:
                raise ValueError(f"{endpoint}: duplicate identifier {identifier}")
            identifiers.add(identifier)
            if endpoint == "automation_rules" and item.get("active") is not False:
                raise ValueError("Automation templates must be inactive until reviewed in the target inbox")
    return manifest


class ChatwootClient:
    def __init__(self, base_url, account_id, token):
        parsed = parse.urlsplit(base_url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or not host or parsed.path not in ("", "/"):
            raise ValueError("CHATWOOT_URL must be a server origin such as https://chat.example.com")
        if parsed.scheme == "http" and host not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("HTTPS is required when sending API tokens to non-local servers")
        if not str(account_id).isdigit() or int(account_id) < 1 or not token:
            raise ValueError("Set valid CHATWOOT_ACCOUNT_ID and CHATWOOT_API_TOKEN")
        self.root = base_url.rstrip("/") + f"/api/v1/accounts/{int(account_id)}"
        self.token = token

    def request_json(self, method, endpoint, body=None):
        path = self.root + "/" + endpoint
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            path,
            data=payload,
            method=method,
            headers={
                "api_access_token": self.token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read(400).decode("utf-8", errors="replace")
            raise RuntimeError(f"{endpoint}: HTTP {exc.code}: {detail}") from None
        except error.URLError as exc:
            raise RuntimeError(f"{endpoint}: network error: {exc.reason}") from None
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            raise RuntimeError(f"{endpoint}: API returned non-JSON data") from None

    def list_resources(self, endpoint):
        result = self.request_json("GET", endpoint)
        if isinstance(result, dict) and "payload" in result:
            result = result["payload"]
        if not isinstance(result, list):
            raise RuntimeError(f"{endpoint}: unexpected response, expected a list")
        return result

    def create_resource(self, endpoint, wrapper, item):
        body = {wrapper: item} if wrapper else item
        return self.request_json("POST", endpoint, body)


def identifier(row, keys):
    return tuple(row.get(key) for key in keys)


def differing_fields(existing, desired):
    return [key for key, value in desired.items() if existing.get(key) != value]


def reconcile(client, manifest, apply=False):
    """Check all resources; create missing entries only with apply=True.

    Existing resources are never overwritten, even if they differ.
    """
    report = {}
    for endpoint, wrapper, keys in RESOURCE_CONFIG:
        current = client.list_resources(endpoint)
        current_by_key = {identifier(row, keys): row for row in current}
        counts = {"present": 0, "created": 0, "missing": [], "different": []}
        for item in manifest[endpoint]:
            key = identifier(item, keys)
            label = "/".join(str(part) for part in key)
            existing = current_by_key.get(key)
            if existing is None:
                if apply:
                    client.create_resource(endpoint, wrapper, item)
                    counts["created"] += 1
                else:
                    counts["missing"].append(label)
            else:
                delta = differing_fields(existing, item)
                if delta:
                    counts["different"].append({"item": label, "fields": delta})
                else:
                    counts["present"] += 1
        if apply and counts["created"]:
            verified = {identifier(row, keys): row for row in client.list_resources(endpoint)}
            for item in manifest[endpoint]:
                key = identifier(item, keys)
                if key not in verified:
                    raise RuntimeError(f"{endpoint}: missing after creation: {key}")
                if key not in current_by_key and differing_fields(verified[key], item):
                    raise RuntimeError(f"{endpoint}: created resource differs from manifest: {key}")
        report[endpoint] = counts
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="SoftMobile sales workspace bootstrap")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="show planned resources without accessing Chatwoot (default)")
    mode.add_argument("--check", action="store_true", help="read-only verification against Chatwoot")
    mode.add_argument("--apply", action="store_true", help="create missing resources; never overwrite")
    parser.add_argument("--manifest", default=str(Path(__file__).with_name("manifest.json")))
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        if not args.check and not args.apply:
            output = {
                "mode": "offline-plan",
                "resources": {endpoint: len(manifest[endpoint]) for endpoint, _, _ in RESOURCE_CONFIG},
                "notes": "No API requests or changes. The automation rule is an inactive draft.",
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        client = ChatwootClient(
            os.environ.get("CHATWOOT_URL", ""),
            os.environ.get("CHATWOOT_ACCOUNT_ID", ""),
            os.environ.get("CHATWOOT_API_TOKEN", ""),
        )
        report = reconcile(client, manifest, apply=args.apply)
        print(json.dumps({"mode": "apply" if args.apply else "check", "report": report}, ensure_ascii=False, indent=2))
        if any(result["missing"] or result["different"] for result in report.values()):
            return 2
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"SoftMobile bootstrap: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
