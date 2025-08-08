#!/usr/bin/env python3
"""Debug script to check JavaScript syntax in quiz.html"""

import re

def check_js_syntax():
    """Check for common JavaScript syntax errors"""
    print("🔍 Checking JavaScript syntax in quiz.html...")
    
    with open('templates/quiz.html', 'r') as f:
        content = f.read()
    
    # Extract JavaScript content
    js_start = content.find('<script>')
    js_end = content.find('</script>')
    
    if js_start == -1 or js_end == -1:
        print("❌ Could not find JavaScript section")
        return False
    
    js_content = content[js_start + 8:js_end]
    lines = js_content.split('\n')
    
    errors = []
    
    # Check for common syntax errors
    brace_count = 0
    paren_count = 0
    in_function = False
    function_brace_count = 0
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip comments and empty lines
        if line.startswith('//') or line.startswith('/*') or not line:
            continue
        
        # Count braces and parentheses
        brace_count += line.count('{') - line.count('}')
        paren_count += line.count('(') - line.count(')')
        
        # Check for function declarations
        if line.startswith('function '):
            in_function = True
            function_brace_count = brace_count
        
        # Check for common syntax errors
        if line.endswith('} else {') and not any(keyword in line for keyword in ['if', 'try', 'catch', 'for', 'while']):
            errors.append(f"Line {i}: Possible orphaned 'else' statement: {line}")
        
        if '}}' in line and not any(keyword in line for keyword in ['//', '/*', 'forEach', 'map', 'filter']):
            errors.append(f"Line {i}: Possible extra closing brace: {line}")
        
        if line.startswith('}') and brace_count < 0:
            errors.append(f"Line {i}: Unmatched closing brace: {line}")
        
        if line.startswith(')') and paren_count < 0:
            errors.append(f"Line {i}: Unmatched closing parenthesis: {line}")
    
    # Final balance check
    if brace_count != 0:
        errors.append(f"Unbalanced braces: {brace_count} extra {'opening' if brace_count > 0 else 'closing'} braces")
    
    if paren_count != 0:
        errors.append(f"Unbalanced parentheses: {paren_count} extra {'opening' if paren_count > 0 else 'closing'} parentheses")
    
    # Report results
    if errors:
        print(f"❌ Found {len(errors)} potential syntax errors:")
        for error in errors:
            print(f"   • {error}")
        return False
    else:
        print("✅ No obvious syntax errors found")
        return True

def check_function_completeness():
    """Check if all functions are properly closed"""
    print("\n🔍 Checking function completeness...")
    
    with open('templates/quiz.html', 'r') as f:
        content = f.read()
    
    # Find all function declarations
    function_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*{'
    functions = re.finditer(function_pattern, content)
    
    incomplete_functions = []
    
    for match in functions:
        func_name = match.group(1)
        func_start = match.start()
        
        # Find the matching closing brace
        brace_count = 0
        pos = func_start
        found_closing = False
        
        while pos < len(content):
            char = content[pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    found_closing = True
                    break
            pos += 1
        
        if not found_closing:
            incomplete_functions.append(func_name)
    
    if incomplete_functions:
        print(f"❌ Found {len(incomplete_functions)} incomplete functions:")
        for func in incomplete_functions:
            print(f"   • {func}")
        return False
    else:
        print("✅ All functions appear to be complete")
        return True

if __name__ == "__main__":
    print("JavaScript Syntax Checker for quiz.html")
    print("=" * 50)
    
    syntax_ok = check_js_syntax()
    functions_ok = check_function_completeness()
    
    if syntax_ok and functions_ok:
        print("\n🎉 JavaScript appears to be syntactically correct!")
        print("   If quiz buttons still don't work, the issue may be:")
        print("   1. CSS styling preventing clicks")
        print("   2. Event handling conflicts")
        print("   3. Network/CORS issues")
        print("   4. Missing dependencies")
    else:
        print("\n⚠️  JavaScript has syntax issues that need to be fixed.")
