import sys
from pathlib import Path

# Permite "import radial" e "import zbrush_bridge" a partir da raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
