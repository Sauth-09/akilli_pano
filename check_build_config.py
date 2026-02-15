
# Validating PyInstaller Spec
import sys
import os

# Mock objects to allow importing the spec file
class MockAnalysis:
    def __init__(self, scripts, pathex, binaries, datas, hiddenimports, hookspath, hooksconfig, runtime_hooks, excludes, noarchive, optimize):
        self.datas = datas
        print("Analysis created with datas count:", len(datas))
        # Print first few to verify
        for d in datas[:5]:
             print("  Included:", d)
        
        # Check for slideshow exclusion
        slideshow_included = False
        for src, dest in datas:
            if 'slideshow' in src and 'static' in src:
                 print(f"WARNING: Found slideshow file: {src} -> {dest}")
                 slideshow_included = True
            
        if not slideshow_included:
             print("SUCCESS: No slideshow files found in datas (checked explicit list).")
        else:
             print("FAILURE: Slideshow files are still included in datas.")

class MockPYZ:
    def __init__(self, *args, **kwargs): pass

class MockEXE:
    def __init__(self, *args, **kwargs): pass

class MockCOLLECT:
    def __init__(self, *args, **kwargs): pass

# Mock Tree
def Tree(root, prefix=None, excludes=None, typecode='DATA'):
    print(f"Tree called with root={root}, prefix={prefix}, excludes={excludes}")
    # Simulate file finding
    # We won't actually walk the fs in this mock, just return a dummy if we wanted.
    # But wait, the spec file calls Tree(). If I don't implement walking, it returns empty list?
    # Or I should let it run if it uses os.walk?
    # Spec implementation of Tree actually walks.
    # Let's import the REAL Tree if possible?
    # It's in PyInstaller.building.datastruct?
    # Hard to import internal PyInstaller classes without PyInstaller installed in env?
    # Assuming PyInstaller IS installed in user env as they are building.
    try:
        from PyInstaller.building.datastruct import Tree as RealTree
        return RealTree(root, prefix=prefix, excludes=excludes, typecode=typecode)
    except ImportError:
        print("PyInstaller not found, using Mock Tree logic.")
        # Minimal mock:
        return [("mock/src/web/static/style.css", "src/web/static/style.css")]

# Inject mocks into builtins or global scope for exec
# Actually better to use exec with a custom globals dict
context = {
    'Analysis': MockAnalysis,
    'PYZ': MockPYZ,
    'EXE': MockEXE,
    'COLLECT': MockCOLLECT,
    'Tree': Tree,
    '__file__': 'AkilliPano.spec'
}

cwd = os.getcwd()
spec_path = os.path.join(cwd, 'AkilliPano.spec')

print(f"Executing spec file: {spec_path}")
with open(spec_path, 'r', encoding='utf-8') as f:
    code = f.read()

try:
    exec(code, context)
    print("Spec file executed successfully.")
except Exception as e:
    print(f"Error executing spec file: {e}")
    import traceback
    traceback.print_exc()
