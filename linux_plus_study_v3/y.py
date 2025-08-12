import ast, os, sys

root = "."
def arglist(a):
    parts = []
    for x in a.posonlyargs: parts.append(x.arg)
    for x in a.args: parts.append(x.arg)
    if a.vararg: parts.append("*" + a.vararg.arg)
    for x in a.kwonlyargs: parts.append(x.arg)
    if a.kwarg: parts.append("**" + a.kwarg.arg)
    return ", ".join(parts)

for path, dirs, files in os.walk(root):
    if "__pycache__" in path: 
        continue
    for f in files:
        if not f.endswith(".py"): 
            continue
        fn = os.path.join(path, f)
        try:
            src = open(fn, "r", encoding="utf-8").read()
            tree = ast.parse(src, filename=fn)
        except Exception as e:
            print(f"# {fn}\nParse error: {e}\n")
            continue

        print(f"# {fn}")
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                print(f"- function {node.name}({arglist(node.args)})")
                doc = ast.get_docstring(node)
                if doc: print(f"  - doc: {doc.splitlines()[0]}")
            elif isinstance(node, ast.ClassDef):
                print(f"## class {node.name}")
                cdoc = ast.get_docstring(node)
                if cdoc: print(f"> {cdoc.splitlines()[0]}")
                for n in node.body:
                    if isinstance(n, ast.FunctionDef):
                        print(f"  - method {n.name}({arglist(n.args)})")
                        d = ast.get_docstring(n)
                        if d: print(f"    - doc: {d.splitlines()[0]}")
        print()
