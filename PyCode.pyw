import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pycode_servidor

pycode_servidor.main(["--janela"])
