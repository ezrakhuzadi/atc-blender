import ast
import unittest
from pathlib import Path


def _find_assert_nodes(tree: ast.AST) -> list[ast.Assert]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]


class TestNoAssertValidation(unittest.TestCase):
    def test_no_assert_statements_in_validation_paths(self):
        repo_root = Path(__file__).resolve().parents[1]
        target_files = [
            "constraint_operations/constraints_helper.py",
            "constraint_operations/dss_constraints_helper.py",
            "flight_feed_operations/views.py",
            "geo_fence_operations/views.py",
            "rid_operations/dss_rid_helper.py",
            "scd_operations/dss_scd_helper.py",
            "scd_operations/utils.py",
            "scd_operations/views.py",
        ]

        failures: list[str] = []
        for relative_path in target_files:
            path = repo_root / relative_path
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            asserts = _find_assert_nodes(tree)
            if asserts:
                line_numbers = sorted({node.lineno for node in asserts if hasattr(node, "lineno")})
                failures.append(f"{relative_path}: assert at lines {line_numbers}")

        if failures:
            self.fail("Unexpected assert statements found:\n" + "\n".join(failures))

