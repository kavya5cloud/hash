"""Hidden pytest tests for the Hash coding benchmark."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


TESTS: dict[str, str] = {
    "code-01": """
def test_add():
    assert add(2, 3) == 5
    assert add(-4, 9) == 5
    assert add(0, 0) == 0
""",
    "code-02": """
def test_is_even():
    assert is_even(2) is True
    assert is_even(7) is False
    assert is_even(0) is True
    assert is_even(-4) is True
""",
    "code-03": """
def test_reverse_string():
    assert reverse_string("hello") == "olleh"
    assert reverse_string("") == ""
    assert reverse_string("a") == "a"
""",
    "code-04": """
def test_count_vowels():
    assert count_vowels("hello") == 2
    assert count_vowels("AEIOU") == 5
    assert count_vowels("xyz") == 0
    assert count_vowels("Beautiful") == 5
""",
    "code-05": """
def test_unique_items():
    assert unique_items([1, 2, 1, 3, 2]) == [1, 2, 3]
    assert unique_items([]) == []
    assert unique_items(["a", "b", "a", "a"]) == ["a", "b"]
""",
    "code-06": """
def test_second_largest():
    assert second_largest([1, 5, 3, 4]) == 4
    assert second_largest([5, 5, 4]) == 4
    assert second_largest([7]) is None
    assert second_largest([2, 2]) is None
""",
    "code-07": """
def test_is_palindrome():
    assert is_palindrome("racecar") is True
    assert is_palindrome("A man, a plan, a canal: Panama") is True
    assert is_palindrome("hello") is False
    assert is_palindrome("") is True
""",
    "code-08": """
def test_word_frequency():
    assert word_frequency("one two one") == {"one": 2, "two": 1}
    assert word_frequency("Hello hello HELLO") == {"hello": 3}
    assert word_frequency("") == {}
""",
    "code-09": """
def test_merge_sorted():
    assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
    assert merge_sorted([], [1, 2]) == [1, 2]
    assert merge_sorted([1, 1], [1]) == [1, 1, 1]
""",
    "code-10": """
def test_binary_search():
    assert binary_search([1, 3, 5, 7], 5) == 2
    assert binary_search([1, 3, 5, 7], 2) == -1
    assert binary_search([], 1) == -1
    assert binary_search([4], 4) == 0
""",
    "code-11": """
def test_rotate_list():
    assert rotate_list([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]
    assert rotate_list([1, 2, 3], 5) == [2, 3, 1]
    assert rotate_list([], 3) == []
    assert rotate_list([1], 100) == [1]
""",
    "code-12": """
def test_flatten_one_level():
    assert flatten_one_level([1, [2, 3], [4]]) == [1, 2, 3, 4]
    assert flatten_one_level([]) == []
    assert flatten_one_level([1, 2, 3]) == [1, 2, 3]
    assert flatten_one_level([[1], [2, 3]]) == [1, 2, 3]
""",
    "code-13": """
def test_first_non_repeating():
    assert first_non_repeating("swiss") == "w"
    assert first_non_repeating("aabbcc") is None
    assert first_non_repeating("aAb") == "a"
    assert first_non_repeating("") is None
""",
    "code-14": """
def test_two_sum():
    result = two_sum([2, 7, 11, 15], 9)
    assert result is not None
    assert result[0] != result[1]
    assert 2 + 7 == 9
    assert two_sum([1, 2, 3], 100) is None
""",
    "code-15": """
def test_longest_increasing_run():
    assert longest_increasing_run([1, 2, 3, 2, 3, 4, 5]) == 4
    assert longest_increasing_run([5, 4, 3]) == 1
    assert longest_increasing_run([]) == 0
    assert longest_increasing_run([1]) == 1
""",
    "code-16": """
def test_valid_parentheses():
    assert valid_parentheses("()[]{}") is True
    assert valid_parentheses("([{}])") is True
    assert valid_parentheses("(]") is False
    assert valid_parentheses("([)") is False
    assert valid_parentheses("") is True
""",
    "code-17": """
def test_group_anagrams():
    result = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    normalized = {frozenset(group) for group in result}
    assert normalized == {
        frozenset({"eat", "tea", "ate"}),
        frozenset({"tan", "nat"}),
        frozenset({"bat"}),
    }
""",
    "code-18": """
def test_shortest_path_grid():
    assert shortest_path_grid([
        [0, 0, 0],
        [1, 1, 0],
        [0, 0, 0],
    ]) == 4
    assert shortest_path_grid([
        [0, 1],
        [1, 0],
    ]) == -1
    assert shortest_path_grid([[0]]) == 0
""",
    "code-19": """
def test_first_duplicate():
    assert first_duplicate([2, 1, 3, 5, 3, 2]) == 3
    assert first_duplicate([1, 2, 3]) is None
    assert first_duplicate([4, 4, 5]) == 4
""",
    "code-20": """
def test_top_k_frequent():
    assert top_k_frequent([1, 1, 1, 2, 2, 3], 2) == [1, 2]
    assert top_k_frequent([4, 4, 5, 5, 6], 2) == [4, 5]
    assert top_k_frequent([1, 2, 3], 5) == [1, 2, 3]
""",
}


def extract_python(output: str) -> str:
    """Extract Python source from a model response."""
    text = output.strip()

    if "```" not in text:
        return text

    parts = text.split("```")
    if len(parts) < 3:
        return text

    code = parts[1]
    if code.lstrip().startswith("python"):
        code = code.lstrip()[6:]

    return code.strip()


def run_hidden_tests(
    task_id: str,
    output: str,
    timeout_seconds: int = 5,
) -> tuple[bool, str]:
    """Run hidden pytest tests against a worker submission."""
    test_body = TESTS.get(task_id)

    if test_body is None:
        return False, f"No hidden tests registered for {task_id}"

    code = extract_python(output)

    with tempfile.TemporaryDirectory(prefix="hash-benchmark-") as directory:
        root = Path(directory)
        solution_path = root / "solution.py"
        test_path = root / "test_solution.py"

        solution_path.write_text(code, encoding="utf-8")
        test_path.write_text(
            "from solution import *\n" + test_body,
            encoding="utf-8",
        )

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    str(test_path),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={
                    "PATH": str(Path(sys.executable).parent),
                    "PYTHONPATH": str(root),
                },
            )
        except subprocess.TimeoutExpired:
            return False, f"Hidden pytest timed out after {timeout_seconds}s"

        if completed.returncode == 0:
            return True, completed.stdout.strip()

        details = (completed.stdout + "\n" + completed.stderr).strip()
        return False, details[-2000:]
