import sys
import os

def main() -> None:
    # Add root directory to sys.path
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    import main as app_main
    app_main.main()
