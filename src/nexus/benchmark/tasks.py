from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

@dataclass
class BenchmarkTask:
    id: str
    category: str
    name: str
    prompt: str
    expected_output: Optional[str] = None
    validation_fn: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

# Standardized set of tasks for evaluation
TASKS = [
    # 1. REASONING
    BenchmarkTask(
        id="reasoning_animal_count",
        category="reasoning",
        name="Animal Heads and Legs Logic Puzzle",
        prompt=(
            "A farmer has 5 chickens and 2 rabbits on his farm. He then buys 3 more chickens, "
            "and unfortunately 1 of the rabbits escapes. "
            "How many animal heads and how many animal legs are left on the farm? "
            "Show your step-by-step reasoning and then output the final count at the very end in the exact format: "
            "'Heads: X, Legs: Y'."
        ),
        expected_output="Heads: 9, Legs: 20",
        validation_fn="validate_reasoning_animals"
    ),
    # 2. PLANNING
    BenchmarkTask(
        id="planning_fastapi_endpoint",
        category="planning",
        name="FastAPI Health Endpoint Plan",
        prompt=(
            "You need to add a new API endpoint `/api/v1/health` to a FastAPI application. "
            "The endpoint must check the health of both the database (PostgreSQL) and the cache (Redis), "
            "and return a JSON response with status 'ok' or 'error' and details for each. "
            "Detail the exact implementation steps as a structured list, indicating any dependencies between steps. "
            "Include setup, connection logic, error handling, and testing."
        ),
        validation_fn="validate_planning_endpoint"
    ),
    # 3. CODE GENERATION
    BenchmarkTask(
        id="code_gen_anagrams",
        category="code_generation",
        name="Find Anagrams Function",
        prompt=(
            "Write a Python function `find_anagrams(word_list: list[str], target: str) -> list[str]` "
            "that takes a list of strings and a target string, and returns a list of all strings from "
            "the word_list that are anagrams of the target string. An anagram is a word formed by rearranging "
            "the letters of another word. The comparison should be case-insensitive. "
            "Output ONLY the Python code block starting with ```python and ending with ```."
        ),
        validation_fn="validate_code_anagrams"
    ),
    # 4. DEBUGGING
    BenchmarkTask(
        id="debugging_remove_duplicates",
        category="debugging",
        name="Remove Duplicates In-Place Bug",
        prompt=(
            "The following Python function is intended to return a list with all duplicate elements removed, "
            "but it contains a critical bug because it modifies the list while iterating over it. "
            "Identify and fix the bug, writing a correct version of `remove_duplicates(lst)`. "
            "Output ONLY the corrected Python code block starting with ```python and ending with ```.\n\n"
            "```python\n"
            "def remove_duplicates(lst):\n"
            "    unique_lst = []\n"
            "    for item in lst:\n"
            "        if item not in unique_lst:\n"
            "            unique_lst.append(item)\n"
            "            lst.remove(item)\n"
            "    return unique_lst\n"
            "```"
        ),
        validation_fn="validate_debugging_duplicates"
    ),
    # 5. TOOL CALLING
    BenchmarkTask(
        id="tool_calling_search",
        category="tool_calling",
        name="Select and Parameterize Search Tool",
        prompt=(
            "You have access to the following tool definitions:\n"
            "1. `read_file(path: str, start_line: int = 1, end_line: int = None) -> str` - Reads a file's content.\n"
            "2. `write_file(path: str, content: str) -> bool` - Writes content to a file.\n"
            "3. `search_text(query: str, path: str) -> list[dict]` - Searches for a text pattern in a file.\n\n"
            "The user asks: 'Find all occurrences of the word \"database\" in the file \"src/config.py\"'.\n"
            "Which tool should be called and what are the exact arguments? "
            "Respond with a JSON object in the format:\n"
            "{\n"
            "  \"tool\": \"tool_name\",\n"
            "  \"args\": {\n"
            "    \"param1\": \"val1\"\n"
            "  }\n"
            "}\n"
            "Output ONLY the JSON block starting with ```json and ending with ```."
        ),
        validation_fn="validate_tool_calling_search"
    ),
    # 6. JSON GENERATION
    BenchmarkTask(
        id="json_gen_release",
        category="json_generation",
        name="Software Release Metadata JSON",
        prompt=(
            "Generate a JSON object representing a software release. The object must contain precisely the following keys:\n"
            "- `version` (string, e.g., '2.1.0')\n"
            "- `release_date` (string in YYYY-MM-DD format)\n"
            "- `features` (array of strings, listing at least 3 features)\n"
            "- `stable` (boolean value)\n\n"
            "Output ONLY the JSON block starting with ```json and ending with ```."
        ),
        validation_fn="validate_json_release"
    )
]
