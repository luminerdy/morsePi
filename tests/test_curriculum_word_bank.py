import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_word_bank():
    module = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "word_practice_bank":
                    return ast.literal_eval(node.value)
    raise AssertionError("word_practice_bank not found")


class CurriculumWordBankTests(unittest.TestCase):
    def test_word_pack_counts_by_unlock_group(self):
        words = load_word_bank()

        starter_so_rk = set("ETANIMSORK")
        starter_so_rk_du = set("ETANIMSORKDU")
        starter_so_rk_du_cwhl = set("ETANIMSORKDUCWHL")

        so_rk_words = [word for word in words if set(word) <= starter_so_rk]
        du_words = [word for word in words if set(word) <= starter_so_rk_du]
        cwhl_words = [word for word in words if set(word) <= starter_so_rk_du_cwhl]

        self.assertEqual(42, len(so_rk_words))
        self.assertEqual(56, len(du_words))
        self.assertEqual(80, len(cwhl_words))
        self.assertNotIn("MOUSE", du_words)
        self.assertIn("CLOCK", cwhl_words)


if __name__ == "__main__":
    unittest.main()
