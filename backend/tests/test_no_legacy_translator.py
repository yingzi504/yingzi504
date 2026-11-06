import ast
import unittest
from pathlib import Path


class NoLegacyTranslatorTests(unittest.TestCase):
    def test_legacy_module_is_removed_and_never_imported(self):
        backend_dir = Path(__file__).resolve().parents[1]
        legacy_module = backend_dir / "app" / "services" / "translator_service_old.py"
        self.assertFalse(legacy_module.exists())

        forbidden = "app.services.translator_service_old"
        references = []
        for path in backend_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                else:
                    continue
                if forbidden in modules:
                    references.append(str(path.relative_to(backend_dir)))

        self.assertEqual(references, [])


if __name__ == "__main__":
    unittest.main()
