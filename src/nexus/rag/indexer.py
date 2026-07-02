import os
import re
from typing import List, Dict, Any

class CodeSymbol:
    def __init__(self, name: str, symbol_type: str, code: str, start_line: int, end_line: int):
        self.name = name
        self.symbol_type = symbol_type # class, function
        self.code = code
        self.start_line = start_line
        self.end_line = end_line

class RepositoryIndexer:
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.files: List[str] = []
        self.symbols: Dict[str, List[CodeSymbol]] = {} # file_path -> symbols

    def scan(self):
        """Scan directory for python files."""
        self.files = []
        self.symbols = {}
        for root, dirs, filenames in os.walk(self.root_dir):
            # Ignore hidden dirs and virtualenvs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "node_modules", "dist")]
            
            for f in filenames:
                if f.endswith(".py"):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    self.files.append(rel_path)
                    self._index_file(rel_path)

    def _index_file(self, rel_path: str):
        """Simple regex-based symbol parser for Python files."""
        try:
            with open(os.path.join(self.root_dir, rel_path), "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return

        file_symbols = []
        
        # Regexes for class and def
        class_pat = re.compile(r"^class\s+(\w+)")
        def_pat = re.compile(r"^def\s+(\w+)")
        
        current_symbol = None
        symbol_code = []
        
        for idx, line in enumerate(lines):
            line_num = idx + 1
            
            # Check for new symbol definition
            class_match = class_pat.match(line)
            def_match = def_pat.match(line)
            
            if class_match or def_match:
                # Save previous symbol if any
                if current_symbol:
                    current_symbol.code = "".join(symbol_code)
                    current_symbol.end_line = line_num - 1
                    file_symbols.append(current_symbol)
                
                name = class_match.group(1) if class_match else def_match.group(1)
                sym_type = "class" if class_match else "function"
                
                current_symbol = CodeSymbol(
                    name=name,
                    symbol_type=sym_type,
                    code="",
                    start_line=line_num,
                    end_line=line_num
                )
                symbol_code = [line]
            else:
                if current_symbol:
                    symbol_code.append(line)
                    
        # Save last symbol
        if current_symbol:
            current_symbol.code = "".join(symbol_code)
            current_symbol.end_line = len(lines)
            file_symbols.append(current_symbol)
            
        self.symbols[rel_path] = file_symbols

    def get_all_symbols(self) -> List[Dict[str, Any]]:
        result = []
        for path, syms in self.symbols.items():
            for s in syms:
                result.append({
                    "file": path,
                    "name": s.name,
                    "type": s.symbol_type,
                    "line_range": f"{s.start_line}-{s.end_line}"
                })
        return result
