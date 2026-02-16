import time

from ..models import Provenance


def normalize_provenance(p: Provenance) -> Provenance:
    if p.ts is None:
        p.ts = time.time()
    return p
