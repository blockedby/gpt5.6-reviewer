from pathlib import Path
import shutil
import tempfile
import unittest

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "agents" / "codex" / "evidence-reviewer.toml"


@unittest.skipIf(tomllib is None, "TOML parsing requires Python 3.11+")
class CodexAdapterTests(unittest.TestCase):
    def test_copied_agent_config_requests_read_only_and_inherits_model(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / ".codex" / "agents" / ADAPTER.name
            destination.parent.mkdir(parents=True)
            shutil.copyfile(ADAPTER, destination)
            with destination.open("rb") as stream:
                config = tomllib.load(stream)

            self.assertEqual(config["name"], "evidence_reviewer")
            self.assertEqual(config["sandbox_mode"], "read-only")
            for field in ("description", "developer_instructions"):
                self.assertIsInstance(config[field], str)
                self.assertTrue(config[field].strip())
            self.assertNotIn("model", config)
            self.assertNotIn("model_reasoning_effort", config)
            self.assertNotIn("mcp_servers", config)


if __name__ == "__main__":
    unittest.main()
