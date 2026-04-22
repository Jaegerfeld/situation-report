import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from transform_data.gui import TransformApp

TransformApp().mainloop()
