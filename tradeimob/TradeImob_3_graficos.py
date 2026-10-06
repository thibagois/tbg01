# Atalho pro menu Workspace > Scripts do DaVinci Resolve.
import runpy, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.argv = ["split_palestras.py", "graficos"]
runpy.run_path(str(here / "split_palestras.py"), run_name="__main__",
               init_globals={"resolve": globals().get("resolve")})
