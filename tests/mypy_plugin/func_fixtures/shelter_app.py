"""Consumer module: uses the `Shelter` model extended in a sibling module.

Importing `shelter_desk` is what makes the extension take effect — mirroring the
runtime, where an extension only augments the model once its module is loaded.
Both the construction keyword and the attribute read below rely on the plugin
understanding the cross-module extension.
"""
from shelter_core import Shelter
from shelter_desk import WelcomeDesk

shelter = Shelter(welcome_desk=WelcomeDesk(name='front'))

# The read type is asserted by the annotation: a mismatch would be an error.
desk: WelcomeDesk = shelter.welcome_desk
