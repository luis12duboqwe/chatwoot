"""Unit tests for the isolated, standard-library SoftMobile setup tool."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import bootstrap


HERE = Path(__file__).resolve().parent


class FakeClient:
    def __init__(self):
        self.store = {endpoint: [] for endpoint, _, _ in bootstrap.RESOURCE_CONFIG}
        self.writes = 0

    def list_resources(self, endpoint):
        return copy.deepcopy(self.store[endpoint])

    def create_resource(self, endpoint, wrapper, item):
        self.writes += 1
        self.store[endpoint].append(copy.deepcopy(item))
        return item


class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = bootstrap.load_manifest(HERE / "manifest.json")

    def test_offline_plan_never_needs_credentials(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = bootstrap.main(["--plan"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "offline-plan")

    def test_create_and_rerun_are_idempotent(self):
        client = FakeClient()
        initial = bootstrap.reconcile(client, self.manifest, apply=False)
        self.assertEqual(sum(len(v["missing"]) for v in initial.values()), 27)
        self.assertEqual(client.writes, 0)

        created = bootstrap.reconcile(client, self.manifest, apply=True)
        self.assertEqual(sum(v["created"] for v in created.values()), 27)
        self.assertEqual(client.writes, 27)

        repeated = bootstrap.reconcile(client, self.manifest, apply=True)
        self.assertEqual(sum(v["created"] for v in repeated.values()), 0)
        self.assertEqual(sum(v["present"] for v in repeated.values()), 27)
        self.assertEqual(client.writes, 27)

    def test_existing_resources_with_manual_changes_are_not_overwritten(self):
        client = FakeClient()
        bootstrap.reconcile(client, self.manifest, apply=True)
        client.store["canned_responses"][0]["content"] = "Personalizado"
        result = bootstrap.reconcile(client, self.manifest, apply=True)
        self.assertEqual(result["canned_responses"]["different"][0]["fields"], ["content"])
        self.assertEqual(client.store["canned_responses"][0]["content"], "Personalizado")
        self.assertEqual(client.writes, 27)

    def test_manifest_rejects_active_automations(self):
        changed = copy.deepcopy(self.manifest)
        changed["automation_rules"][0]["active"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inactive"):
                bootstrap.load_manifest(path)

    def test_manifest_rejects_duplicate_resources(self):
        changed = copy.deepcopy(self.manifest)
        changed["labels"].append(changed["labels"][0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                bootstrap.load_manifest(path)

    def test_protect_api_token_from_insecure_remote_http(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            bootstrap.ChatwootClient("http://chat.example.com", "1", "secret")
        client = bootstrap.ChatwootClient("http://127.0.0.1:3000", "12", "secret")
        self.assertTrue(client.root.endswith("/api/v1/accounts/12"))

    def test_invalid_api_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            bootstrap.ChatwootClient("https://example.com/app", "1", "secret")


if __name__ == "__main__":
    unittest.main()
