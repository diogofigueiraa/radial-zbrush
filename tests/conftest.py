import sys
from pathlib import Path

# Allows "import radial" and "import zbrush_bridge" from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
