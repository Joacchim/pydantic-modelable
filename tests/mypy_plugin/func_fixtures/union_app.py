"""Consumer of the cross-module discriminated union.

`Envelope.payload` is only usable as a discriminated union if the plugin has
aggregated the subtypes contributed by the sibling extension modules.
"""
from union_core import Envelope
from union_temp import Temperature

envelope = Envelope(seq=1, payload=Temperature(celsius=21.5))

# Discriminated narrowing across module boundaries: valid only when `payload`
# is typed as the union of the sibling modules' subtypes.
if envelope.payload.kind == 'temperature':
    reading: float = envelope.payload.celsius
