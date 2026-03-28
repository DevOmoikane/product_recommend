import importlib
import pkgutil

def load_plugins(package_name: str):
    """
    Recursively load all plugins from a package and its subpackages.
    This will import all modules, executing any decorators in the process.
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        print(f"Warning: Could not import package {package_name}")
        return

    # Get the package path - handle both single packages and namespace packages
    if hasattr(package, '__path__'):
        package_paths = package.__path__
    else:
        # For modules without __path__, we can't iterate submodules
        return

    # Use pkgutil.walk_packages for recursive traversal
    for module_info in pkgutil.walk_packages(
        path=package_paths,
        prefix=f"{package_name}.",
        onerror=lambda x: print(f"Warning: Error loading {x}")
    ):
        try:
            importlib.import_module(module_info.name)
            print(f"Loaded plugin: {module_info.name}")
        except Exception as e:
            print(f"Warning: Could not load plugin {module_info.name}: {e}")
