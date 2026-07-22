"""
Environment Verification Script
Run this to ensure all dependencies are installed correctly.
"""

import sys
import importlib
import os


def check_package(package_name, import_name=None):
    """
    Check if a package is installed.
    
    Args:
        package_name (str): Name of the package to check
        import_name (str, optional): Import name if different from package name
    
    Returns:
        bool: True if installed, False otherwise
    """
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name} - OK")
        return True
    except ImportError:
        print(f"❌ {package_name} - MISSING")
        return False


def check_folder(folder_name):
    """
    Check if a folder exists in the project.
    
    Args:
        folder_name (str): Name of the folder
    
    Returns:
        bool: True if exists, False otherwise
    """
    if os.path.exists(folder_name) and os.path.isdir(folder_name):
        print(f"✅ {folder_name}/ - OK")
        return True
    else:
        print(f"❌ {folder_name}/ - MISSING")
        return False


def check_file(file_name):
    """
    Check if a file exists in the project.
    
    Args:
        file_name (str): Name of the file
    
    Returns:
        bool: True if exists, False otherwise
    """
    if os.path.exists(file_name) and os.path.isfile(file_name):
        print(f"✅ {file_name} - OK")
        return True
    else:
        print(f"❌ {file_name} - MISSING")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🔍 ENVIRONMENT VERIFICATION")
    print("=" * 60)
    
    # Check Python version
    print(f"\n🐍 Python Version: {sys.version}")
    print(f"📍 Python Location: {sys.executable}")
    
    # Check if virtual environment is active
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    if in_venv:
        print("✅ Virtual Environment: ACTIVE")
    else:
        print("⚠️  Virtual Environment: NOT ACTIVE (Recommended to use venv)")
    
    print("\n" + "=" * 60)
    print("📦 Checking Required Packages")
    print("=" * 60)
    
    # Check required packages
    packages = [
        ('cryptography', None),
        ('matplotlib', None),
        ('pandas', None),
        ('numpy', None),
        ('pytest', None),
        ('tabulate', None),
        ('pyyaml', 'yaml'),
    ]
    
    all_packages_ok = True
    for package_name, import_name in packages:
        if not check_package(package_name, import_name):
            all_packages_ok = False
    
    print("\n" + "=" * 60)
    print("📂 Checking Project Structure")
    print("=" * 60)
    
    # Check required folders
    folders = [
        'src',
        'src/config',
        'src/core',
        'src/engines',
        'src/analyzers',
        'src/utils',
        'src/cli',
        'tests',
        'tests/fixtures',
        'docs',
        'docs/diagrams',
        'docs/team',
        'data',
        'data/input',
        'data/encrypted',
        'data/decrypted',
        'data/keys',
        'results',
        'results/graphs',
        'results/csv',
        'results/logs',
        'results/demo_outputs',
        'benchmarks',
        'benchmarks/datasets',
        'benchmarks/configs',
        'benchmarks/scripts',
        'assets',
        'assets/images',
        '.github',
        '.github/ISSUE_TEMPLATE',
        'reports',
    ]
    
    all_folders_ok = True
    for folder in folders:
        if not check_folder(folder):
            all_folders_ok = False
    
    print("\n" + "=" * 60)
    print("📄 Checking Important Files")
    print("=" * 60)
    
    # Check required files
    files = [
        'README.md',
        'requirements.txt',
        '.gitignore',
        'setup.py',
        'CHANGELOG.md',
        'CONTRIBUTING.md',
        'CONTRIBUTORS.md',
        'WORKFLOW.md',
        'src/__init__.py',
        'src/config/__init__.py',
        'src/core/__init__.py',
        'src/engines/__init__.py',
        'src/analyzers/__init__.py',
        'src/utils/__init__.py',
        'src/cli/__init__.py',
        'tests/__init__.py',
    ]
    
    all_files_ok = True
    for file in files:
        if not check_file(file):
            all_files_ok = False
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    # Final summary
    if all_packages_ok and all_folders_ok and all_files_ok:
        print("\n✅ ALL CHECKS PASSED!")
        print("🎉 Environment is ready for development.")
        print("\n📝 Next Steps:")
        print("  1. Activate virtual environment: venv\\Scripts\\activate")
        print("  2. Start coding on your feature branch")
        print("  3. Test each module as you build")
    else:
        print("\n⚠️  SOME CHECKS FAILED!")
        print("\n🔧 To fix issues:")
        
        if not all_packages_ok:
            print("  • Install missing packages: pip install -r requirements.txt")
        
        if not all_folders_ok:
            print("  • Create missing folders")
            print("  • Ensure you're in the correct project root")
        
        if not all_files_ok:
            print("  • Create missing files")
            print("  • Ensure you're in the correct project root")
    
    print("\n" + "=" * 60)
    print("🔍 Git Status Check")
    print("=" * 60)
    
    # Check Git status
    try:
        import subprocess
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout:
            print("📝 Uncommitted changes detected:")
            print(result.stdout)
        else:
            print("✅ Working tree clean - no uncommitted changes")
        
        # Check current branch
        branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                     capture_output=True, text=True)
        if branch_result.stdout:
            print(f"🌿 Current Branch: {branch_result.stdout.strip()}")
    except Exception as e:
        print("⚠️  Could not check Git status:", str(e))
    
    print("\n" + "=" * 60)
    print("✅ Verification Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main() 
