"""add_ticker places new rows in a sorted section so parallel additions rarely conflict."""
import unittest

import add_ticker

ENGINE = """X = 1
DATA = {
'ZZ': dict(yf='ZZ', fcf=1),
# --- curated group comment ---
'AA': dict(yf='AA', fcf=1,
    sub=(1, 2)),
}

# ---------------- engine ----------------
"""


def add(text, key):
    position, prefix = add_ticker.insertion_point(text, key)
    return text[:position] + prefix + f"'{key}': dict(yf='{key}'),\n" + text[position:]


def keys(text):
    return [line.split("'")[1] for line in text.splitlines() if line.startswith("'")]


class InsertionPointTests(unittest.TestCase):
    def test_first_addition_opens_the_sorted_section_before_the_closing_brace(self):
        text = add(ENGINE, 'MM')
        self.assertEqual(keys(text), ['ZZ', 'AA', 'MM'])
        self.assertIn(add_ticker.AUTO_SECTION + "\n'MM'", text)
        self.assertIn("'MM': dict(yf='MM'),\n}\n", text)
        compile(text, 'engine.py', 'exec')

    def test_later_additions_are_sorted_inside_the_section_only(self):
        text = ENGINE
        for key in ('O', 'GOOGL', 'CLX', 'AMD', 'ZTS'):
            text = add(text, key)
        self.assertEqual(keys(text), ['ZZ', 'AA', 'AMD', 'CLX', 'GOOGL', 'O', 'ZTS'])
        self.assertEqual(text.count(add_ticker.AUTO_SECTION), 1)
        self.assertIn("# --- curated group comment ---\n'AA'", text)
        compile(text, 'engine.py', 'exec')

    def test_parallel_additions_get_different_insertion_points(self):
        base = add(add(ENGINE, 'CLX'), 'O')
        self.assertNotEqual(add_ticker.insertion_point(base, 'AMD'),
                            add_ticker.insertion_point(base, 'GOOGL'))

    def test_real_engine_insertion_compiles(self):
        with open('engine.py', encoding='utf-8') as handle:
            source = handle.read()
        candidate = add(source, 'ZZZTEST')
        compile(candidate, 'engine.py', 'exec')
        self.assertLess(candidate.index("'ZZZTEST'"), candidate.index('# ---------------- engine'))


if __name__ == '__main__':
    unittest.main()
