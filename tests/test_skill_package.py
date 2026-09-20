from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SCHEMA_DIR = ROOT / "schemas"
SKILL_SOURCE = ROOT / "skills" / "code-review"
EXPECTED_SCHEMA_NAMES = (
    "finding.schema.json",
    "review-request.schema.json",
    "review-result.schema.json",
)


class SkillPackageTests(unittest.TestCase):
    def _load_json(self, path: Path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self.fail(f"could not load JSON schema {path}: {error}")

    def _copy_skill(self, temporary_directory: str):
        isolated_skill = Path(temporary_directory) / "skills" / "code-review"
        shutil.copytree(SKILL_SOURCE, isolated_skill)
        return isolated_skill

    def _iter_refs(self, value):
        if isinstance(value, dict):
            if "$ref" in value:
                yield value["$ref"]
            for child in value.values():
                yield from self._iter_refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._iter_refs(child)

    def _resolve_local_ref(
        self,
        source_schema: Path,
        reference: str,
        isolated_skill: Path,
    ):
        self.assertIsInstance(reference, str)
        reference_path = reference.split("#", 1)[0]
        if not reference_path:
            return None

        parsed_reference = urlsplit(reference_path)
        if parsed_reference.scheme or parsed_reference.netloc:
            return None

        target = (source_schema.parent / unquote(parsed_reference.path)).resolve()
        isolated_root = isolated_skill.resolve()
        try:
            target.relative_to(isolated_root)
        except ValueError:
            self.fail(
                f"local $ref escapes isolated skill: {source_schema} -> {reference}"
            )
        return target

    def _load_schema_graph(
        self,
        packaged_schema_paths: list[Path],
        isolated_skill: Path,
    ):
        pending = [path.resolve() for path in packaged_schema_paths]
        loaded: dict[Path, dict] = {}

        while pending:
            schema_path = pending.pop()
            if schema_path in loaded:
                continue

            schema = self._load_json(schema_path)
            self.assertIsInstance(schema, dict, f"schema is not an object: {schema_path}")
            loaded[schema_path] = schema

            for reference in self._iter_refs(schema):
                target = self._resolve_local_ref(
                    schema_path,
                    reference,
                    isolated_skill,
                )
                if target is None:
                    continue
                self.assertTrue(
                    target.is_file(),
                    f"local $ref does not resolve: {schema_path} -> {reference}",
                )
                pending.append(target)

        return loaded

    def test_skill_copy_preserves_schema_layout_and_canonical_content(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            isolated_skill = self._copy_skill(temporary_directory)
            packaged_schema_dir = isolated_skill / "schemas"

            self.assertTrue((isolated_skill / "SKILL.md").is_file())
            self.assertTrue((isolated_skill / "verifier-prompt.md").is_file())
            self.assertTrue(packaged_schema_dir.is_dir())

            canonical_schema_paths = sorted(CANONICAL_SCHEMA_DIR.glob("*.schema.json"))
            packaged_schema_paths = sorted(packaged_schema_dir.rglob("*.schema.json"))
            self.assertEqual(
                [path.name for path in canonical_schema_paths],
                list(EXPECTED_SCHEMA_NAMES),
            )
            self.assertEqual(
                [
                    path.relative_to(packaged_schema_dir).as_posix()
                    for path in packaged_schema_paths
                ],
                list(EXPECTED_SCHEMA_NAMES),
            )

            for canonical_path, packaged_path in zip(
                canonical_schema_paths,
                packaged_schema_paths,
            ):
                with self.subTest(schema=canonical_path.name):
                    self.assertEqual(
                        self._load_json(packaged_path),
                        self._load_json(canonical_path),
                    )

            loaded = self._load_schema_graph(
                packaged_schema_paths,
                isolated_skill,
            )
            self.assertTrue(
                {path.resolve() for path in packaged_schema_paths}.issubset(loaded),
                "not all packaged schemas were loaded",
            )


if __name__ == "__main__":
    unittest.main()
