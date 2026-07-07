"""Consumer referencing the dynamically-injected enum members by name."""
from enum_blue import Blue
from enum_core import Palette
from enum_red import Red

red: Palette = Palette.red
blue: Palette = Palette.blue

_r = Red
_b = Blue
