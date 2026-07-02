import re
import json
import traceback
from typing import Any, Dict, List, Tuple
from nexus.benchmark.tasks import BenchmarkTask

def extract_code_block(text: str, language: str = "python") -> str:
    """Extract code block of a given language from markdown."""
    pattern = rf"```(?:{language})?\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback: if no backticks, try to find code by patterns
    if language == "python":
        # Look for def ...:
        def_match = re.search(r"(def\s+\w+\s*\(.*?\):.*)", text, re.DOTALL)
        if def_match:
            return def_match.group(1).strip()
    elif language == "json":
        # Look for first { and last }
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
            
    return text.strip()

def validate_reasoning_animals(raw_output: str, task: BenchmarkTask) -> Tuple[bool, Dict[str, Any]]:
    """Validate reasoning puzzle."""
    # Look for "Heads: 9" and "Legs: 20"
    heads_match = re.search(r"Heads:\s*(\d+)", raw_output, re.IGNORECASE)
    legs_match = re.search(r"Legs:\s*(\d+)", raw_output, re.IGNORECASE)
    
    success = False
    details = {}
    
    if heads_match and legs_match:
        heads = int(heads_match.group(1))
        legs = int(legs_match.group(1))
        details["heads"] = heads
        details["legs"] = legs
        if heads == 9 and legs == 20:
            success = True
    else:
        details["error"] = "Could not find 'Heads: X, Legs: Y' pattern in output."
        
    return success, details

def validate_planning_endpoint(raw_output: str, task: BenchmarkTask) -> Tuple[bool, Dict[str, Any]]:
    """Validate planning task using keyword heuristics."""
    keywords = ["fastapi", "database", "redis", "/api/v1/health"]
    passed_keywords = []
    
    for kw in keywords:
        # Check case-insensitive
        if re.search(re.escape(kw), raw_output, re.IGNORECASE):
            passed_keywords.append(kw)
            
    # Planning is successful if it covers all key requirements (at least 3 out of 4)
    success = len(passed_keywords) >= 3
    details = {
        "passed_keywords": passed_keywords,
        "missing_keywords": [kw for kw in keywords if kw not in passed_keywords]
    }
    return success, details

def validate_code_anagrams(raw_output: str, task: BenchmarkTask) -> Tuple[bool, Dict[str, Any]]:
    """Validate anagrams code generation by executing it against test cases."""
    code = extract_code_block(raw_output, "python")
    details = {"extracted_code": code}
    
    # Try compiling first
    try:
        compiled = compile(code, "<string>", "exec")
        details["compile_success"] = True
    except Exception as e:
        details["compile_success"] = False
        details["error"] = f"Compile error: {str(e)}"
        return False, details

    # Try executing test cases
    try:
        local_vars = {}
        exec(compiled, {}, local_vars)
        
        if "find_anagrams" not in local_vars:
            details["error"] = "Function 'find_anagrams' not defined in the code."
            return False, details
            
        find_anagrams = local_vars["find_anagrams"]
        
        # Test Case 1: Standard
        tc1 = find_anagrams(["listen", "silent", "hello", "enlist"], "silent")
        # Sort results to compare
        tc1_sorted = sorted([w.lower() for w in tc1])
        expected1 = sorted(["listen", "silent", "enlist"])
        assert tc1_sorted == expected1, f"Failed test case 1: got {tc1}, expected {expected1}"
        
        # Test Case 2: Case insensitivity
        tc2 = find_anagrams(["Listen", "silent", "World"], "Silent")
        tc2_sorted = sorted([w.lower() for w in tc2])
        expected2 = sorted(["listen", "silent"])
        assert tc2_sorted == expected2, f"Failed test case 2 (case insensitivity): got {tc2}, expected {expected2}"
        
        # Test Case 3: No matches
        tc3 = find_anagrams(["abc", "def"], "xyz")
        assert tc3 == [], f"Failed test case 3: got {tc3}, expected []"
        
        details["test_success"] = True
        return True, details
        
    except Exception as e:
        details["test_success"] = False
        details["error"] = f"Runtime/Assertion error: {str(e)}\n{traceback.format_exc()}"
        return False, details

def validate_debugging_duplicates(raw_output: str, task: BenchmarkTask) -> Tuple[bool, Dict[str, Any]]:
    """Validate duplicate removal debugging task by executing it against test cases."""
    code = extract_code_block(raw_output, "python")
    details = {"extracted_code": code}
    
    # Try compiling first
    try:
        compiled = compile(code, "<string>", "exec")
        details["compile_success"] = True
    except Exception as e:
        details["compile_success"] = False
        details["error"] = f"Compile error: {str(e)}"
        return False, details

    # Try executing test cases
    try:
        local_vars = {}
        exec(compiled, {}, local_vars)
        
        if "remove_duplicates" not in local_vars:
            details["error"] = "Function 'remove_duplicates' not defined in the code."
            return False, details
            
        remove_duplicates = local_vars["remove_duplicates"]
        
        # Test Case 1: Standard duplicates
        tc1 = remove_duplicates([1, 2, 2, 3, 1, 4])
        assert list(tc1) == [1, 2, 3, 4], f"Failed test case 1: got {tc1}, expected [1, 2, 3, 4]"
        
        # Test Case 2: Empty list
        tc2 = remove_duplicates([])
        assert list(tc2) == [], f"Failed test case 2: got {tc2}, expected []"
        
        # Test Case 3: All duplicates
        tc3 = remove_duplicates([5, 5, 5])
        assert list(tc3) == [5], f"Failed test case 3: got {tc3}, expected [5]"
        
        details["test_success"] = True
        return True, details
        
    except Exception as e:
        details["test_success"] = False
        details["error"] = f"Runtime/Assertion error: {str(e)}\n{traceback.format_exc()}"
        return False, details

def validate_tool_calling_search(raw_output: str, task: BenchmarkTask) -> Tuple[bool, Dict[str, Any]]:
    """Validate tool calling JSON output."""
    json_str = extract_code_block(raw_output, "json")
    details = {"extracted_json": json_str}
    
    try:
        data = json.loads(json_str)
        details["parse_success"] = True
    except Exception as e:
        details["parse_success"] = False
        details["error"] = f"JSON parse error: {str(e)}"
        return False, details
        
    # Check tool and args
    tool = data.get("tool", "")
    args = data.get("args", {})
    
    details["tool"] = tool
    details["args"] = args
    
    if tool != "search_text":
        details["error"] = f"Incorrect tool selected: got '{tool}', expected 'search_text'"
        return False, details
        
    query = args.get("query", "")
    path = args.get("path", "")
    
    if query.lower() != "database":
        details["error"] = f"Incorrect query argument: got '{query}', expected 'database'"
        return False, details
        
    if path != "src/config.py":
        details["error"] = f"Incorrect path argument: got '{path}', expected 'src/config.py'"
        return False, details
        
    details["tool_accuracy"] = 1.0
    return True, details

def validate_json_release(raw_output: str, task: BenchmarkTask) -> Tuple[bool, Dict[str, Any]]:
    """Validate release metadata JSON generation."""
    json_str = extract_code_block(raw_output, "json")
    details = {"extracted_json": json_str}
    
    try:
        data = json.loads(json_str)
        details["parse_success"] = True
    except Exception as e:
        details["parse_success"] = False
        details["error"] = f"JSON parse error: {str(e)}"
        return False, details
        
    # Check fields
    required_keys = ["version", "release_date", "features", "stable"]
    missing_keys = [k for k in required_keys if k not in data]
    
    if missing_keys:
        details["error"] = f"Missing required keys: {missing_keys}"
        return False, details
        
    # Validate types and values
    version = data["version"]
    release_date = data["release_date"]
    features = data["features"]
    stable = data["stable"]
    
    if not isinstance(version, str):
        details["error"] = "Field 'version' must be a string."
        return False, details
        
    if not isinstance(release_date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", release_date):
        details["error"] = "Field 'release_date' must be a string in YYYY-MM-DD format."
        return False, details
        
    if not isinstance(features, list) or len(features) < 3 or not all(isinstance(f, str) for f in features):
        details["error"] = "Field 'features' must be an array of at least 3 strings."
        return False, details
        
    if not isinstance(stable, bool):
        details["error"] = "Field 'stable' must be a boolean."
        return False, details
        
    return True, details

# Map validation function names to actual functions
VALIDATORS = {
    "validate_reasoning_animals": validate_reasoning_animals,
    "validate_planning_endpoint": validate_planning_endpoint,
    "validate_code_anagrams": validate_code_anagrams,
    "validate_debugging_duplicates": validate_debugging_duplicates,
    "validate_tool_calling_search": validate_tool_calling_search,
    "validate_json_release": validate_json_release
}

def evaluate_task(task: BenchmarkTask, raw_output: str) -> Tuple[bool, Dict[str, Any]]:
    """Route task to its corresponding validation function."""
    val_fn_name = task.validation_fn
    if val_fn_name in VALIDATORS:
        return VALIDATORS[val_fn_name](raw_output, task)
    else:
        # Default fallback: check if expected_output is in raw_output
        if task.expected_output:
            success = task.expected_output.lower() in raw_output.lower()
            return success, {"method": "substring_match"}
        return True, {"method": "no_validation"}
