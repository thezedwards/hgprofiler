import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))

from cli.debug import DebugCli
DebugCli().run()
