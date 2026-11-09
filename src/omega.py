"""Shared RNG helper for F0.

omega is always a numpy SeedSequence.  Callers build the SeedSequence and
this module only derives named streams from it.
"""

from __future__ import annotations

from numpy.random import Generator, PCG64, SeedSequence


def omega_rng(omega: SeedSequence, j: int) -> Generator:
    """Return Generator stream j derived from a SeedSequence.

    Stream 0 is the INIT stream.  Stream 1+r is the candidate-permutation
    stream of birth round r.  The streams depend only on ``omega`` and ``j``,
    never on S or on the observed image y.
    """
    return Generator(
        PCG64(
            SeedSequence(
                entropy=omega.entropy,
                spawn_key=tuple(omega.spawn_key) + (int(j),),
            )
        )
    )
