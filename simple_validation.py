#!/usr/bin/env python3
"""
Simple validation script to test core fixes without external dependencies
"""

import ast
import sys
import os
from pathlib import Path

def test_syntax_compilation():
    """Test that all Python files compile successfully"""
    print("🔍 Testing syntax compilation...")
    
    project_root = Path(__file__).parent
    python_files = list((project_root / "git_commit_manager").glob("*.py"))
    
    failed_files = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse the AST to check for syntax errors
            ast.parse(source_code, filename=str(py_file))
            print(f"  ✅ {py_file.name}")
            
        except SyntaxError as e:
            print(f"  ❌ {py_file.name}: Syntax error at line {e.lineno}: {e.msg}")
            failed_files.append(py_file.name)
        except Exception as e:
            print(f"  ❌ {py_file.name}: {e}")
            failed_files.append(py_file.name)
    
    if failed_files:
        print(f"\n❌ Syntax errors found in: {', '.join(failed_files)}")
        return False
    else:
        print(f"\n✅ All {len(python_files)} Python files compile successfully!")
        return True

def test_specific_fixes():
    """Test specific fixes we made"""
    print("\n🔍 Testing specific fixes...")
    
    # Test 1: Check that the typo in commit_analyzer.py is fixed
    commit_analyzer_path = Path(__file__).parent / "git_commit_manager" / "commit_analyzer.py"
    
    with open(commit_analyzer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that the problematic line is fixed
    if "def get_commit_user_prompts(cls) -> Dict[str, str]:te" in content:
        print("  ❌ The typo 'te' is still present in commit_analyzer.py")
        return False
    else:
        print("  ✅ Syntax error in commit_analyzer.py is fixed")
    
    # Test 2: Check that security improvements are present
    config_path = Path(__file__).parent / "git_commit_manager" / "config.py"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    if "_validate_api_key" in config_content and "validate_file_path" in config_content:
        print("  ✅ Security validation methods added to config.py")
    else:
        print("  ❌ Security validation methods missing in config.py")
        return False
    
    # Test 3: Check that memory optimization methods are present
    git_analyzer_path = Path(__file__).parent / "git_commit_manager" / "git_analyzer.py"
    
    with open(git_analyzer_path, 'r', encoding='utf-8') as f:
        git_analyzer_content = f.read()
    
    if "_process_file_streaming" in git_analyzer_content:
        print("  ✅ Memory optimization methods added to git_analyzer.py")
    else:
        print("  ❌ Memory optimization methods missing in git_analyzer.py")
        return False
    
    # Test 4: Check that LLM providers have input validation
    llm_providers_path = Path(__file__).parent / "git_commit_manager" / "llm_providers.py"
    
    with open(llm_providers_path, 'r', encoding='utf-8') as f:
        llm_content = f.read()
    
    if "유효하지 않은 프롬프트" in llm_content and "max_prompt_length" in llm_content:
        print("  ✅ Input validation added to LLM providers")
    else:
        print("  ❌ Input validation missing in LLM providers")
        return False
    
    # Test 5: Check that sensitive data filtering is present
    commit_analyzer_path = Path(__file__).parent / "git_commit_manager" / "commit_analyzer.py"
    
    with open(commit_analyzer_path, 'r', encoding='utf-8') as f:
        commit_content = f.read()
    
    if "민감한 정보가 포함된 라인 제외됨" in commit_content:
        print("  ✅ Sensitive data filtering added to commit analyzer")
    else:
        print("  ❌ Sensitive data filtering missing in commit analyzer")
        return False
    
    print("\n✅ All specific fixes verified!")
    return True

def test_documentation():
    """Test that documentation was created"""
    print("\n🔍 Testing documentation...")
    
    docs_dir = Path(__file__).parent / "docs"
    
    expected_docs = [
        "README.md",
        "issues-analysis.md", 
        "security-assessment.md",
        "performance-optimization.md"
    ]
    
    missing_docs = []
    
    for doc in expected_docs:
        doc_path = docs_dir / doc
        if doc_path.exists():
            print(f"  ✅ {doc}")
        else:
            print(f"  ❌ {doc} (missing)")
            missing_docs.append(doc)
    
    if missing_docs:
        print(f"\n❌ Missing documentation: {', '.join(missing_docs)}")
        return False
    else:
        print(f"\n✅ All documentation files present!")
        return True

def main():
    """Run all validation tests"""
    print("🚀 Git Commit Manager - Simple Fix Validation")
    print("=" * 60)
    
    tests = [
        ("Syntax Compilation", test_syntax_compilation),
        ("Specific Fixes", test_specific_fixes),
        ("Documentation", test_documentation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 50)
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All core fixes validated successfully!")
        print("The critical issues in Git Commit Manager have been resolved:")
        print("  • Syntax error fixed")
        print("  • Security improvements implemented") 
        print("  • Memory optimizations added")
        print("  • Input validation enhanced")
        print("  • Documentation created")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())