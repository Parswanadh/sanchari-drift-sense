# Honest Failure Case: pair_0019

- Architecture: finfet
- Had unique site marker: False
- True location: (675.0, 599.6)
- Predicted location: (361.0, 285.0)
- Pixel error: 444.46px
- Match confidence score: 0.626
- Periodic ambiguity flagged by algorithm: True

## Root cause

This pair had no locally-unique site marker (has_unique_marker=False): the reference crop sits in a purely periodic region of the array, so many lattice repeats are statistically indistinguishable from the true site.

Applied Materials' own stated disambiguation rule -- among tied/near-tied matches, prefer
whichever is closest to the search image's center -- is applied by localize.py, but that
rule only recovers the *correct* site when the true site happens to be the center-closest
repeat. In a genuinely periodic, marker-free region, there is no image content that could
ever distinguish the true site from its lattice neighbors from a single reference crop alone;
this is a fundamental information-theoretic limit of template matching on periodic layouts,
not a bug in the search strategy. This is precisely the class of case Applied Materials
flags as "genuinely difficult" navigation-error recovery.
