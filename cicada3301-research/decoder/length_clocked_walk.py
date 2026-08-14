#!/usr/bin/env python3
"""length_clocked_walk.py — Length-clocked progressive substitution cipher.

Task ID: p8i (Phase H — length-clocked-walk implementation/attack)

This implements the aldegonde "length-clocked-walk" model:

    c[j] = base_w( g^(j mod 5)( p[j] ) )                          [within word]
    base_{w+1} = base_w ∘ g^((L_w - 1) mod 5) ∘ σ                  [word step]

Key = (base_0, g, σ): three permutations on 0..28 (29 runes); g has order 5
(g^5 = identity). The per-word base is a deterministic walk clocked by the
PUBLIC word lengths, so decryption is exact given the key:

    p[j] = g^-(j mod 5)( base_w^-1( c[j] ) )

Total key ≈ 200 bits. Permutations are lists p with p[i] = image of i;
compose(a,b)[i] = a[b[i]].
"""
from __future__ import annotations
import math
import random
import sys
from pathlib import Path

M = 29

# ============================================================================
# PERMUTATION PRIMITIVES
# ============================================================================
def perm_compose(a: list[int], b: list[int]) -> list[int]:
    """(a ∘ b)[i] = a[b[i]]."""
    return [a[b[i]] for i in range(len(b))]


def perm_inverse(p: list[int]) -> list[int]:
    inv = [0] * len(p)
    for i, x in enumerate(p):
        inv[x] = i
    return inv


def perm_power(p: list[int], n: int) -> list[int]:
    """Compute p^n (n>=0). Negative n => inverse powers."""
    if n == 0:
        return list(range(len(p)))
    if n < 0:
        return perm_power(perm_inverse(p), -n)
    out = list(range(len(p)))
    for _ in range(n):
        out = perm_compose(p, out)
    return out


def is_order_5(g: list[int]) -> bool:
    """Verify g^5 == identity."""
    return perm_power(g, 5) == list(range(len(g)))


def random_order_5_permutation(rng: random.Random | None = None) -> list[int]:
    """Random order-5 permutation on 29 elements.

    29 = 5*5 + 4 → five disjoint 5-cycles + four fixed points.
    Construction: shuffle 29 elements, take 5 columns of a 5×5 grid as cycles.
    """
    if rng is None:
        rng = random.Random()
    perm = list(range(M))
    rng.shuffle(perm)
    g = list(range(M))
    # 5 five-cycles: each column of a 5×5 grid is a 5-cycle
    for col in range(5):
        cells = [perm[row * 5 + col] for row in range(5)]
        for row in range(5):
            g[cells[row]] = cells[(row + 1) % 5]
    # Last 4 elements (perm[25:29]) stay fixed (already identity)
    assert is_order_5(g), "bug: generated g is not order 5"
    return g


# ============================================================================
# CIPHER CLASS
# ============================================================================
class LengthClockedWalk:
    """The length-clocked progressive substitution (aldegonde's leading
    hypothesis for unsolved Liber Primus).

    State: (base, g, sigma). base evolves word-by-word; g applied per-letter
    within the word; sigma applied at each word boundary.
    """

    def __init__(self, base_0, g, sigma):
        if not is_order_5(g):
            raise ValueError("g must be an order-5 permutation (g^5 = id)")
        if sorted(base_0) != list(range(M)):
            raise ValueError("base_0 must be a permutation of 0..28")
        if sorted(sigma) != list(range(M)):
            raise ValueError("sigma must be a permutation of 0..28")
        self.base = list(base_0)
        self.g = list(g)
        self.sigma = list(sigma)
        # Precompute g^0..g^4 and g^-0..g^-4 for speed
        self._gp = [perm_power(self.g, k) for k in range(5)]
        self._gpinv = [perm_inverse(p) for p in self._gp]

    def g_pow(self, k: int) -> list[int]:
        """Return g^k (k taken mod 5 since g has order 5)."""
        return self._gp[k % 5]

    def decrypt_word(self, ct_runes: list[int], word_length: int) -> list[int]:
        """Decrypt a single word and advance the base state for the next word.

        ct_runes: list of ciphertext rune indices (0..28).
        word_length: L_w, used to update the base for the next word.
                     (We accept word_length explicitly because the public word
                     lengths are part of the key schedule, not the secret.)
        Returns: list of plaintext rune indices.
        """
        binv = perm_inverse(self.base)
        pt = []
        for j, c in enumerate(ct_runes):
            # c = base(g^(j%5)(p))  →  p = g^-(j%5)(base^-1(c))
            p = self._gpinv[j % 5][binv[c]]
            pt.append(p)
        # Update base for next word: base = base ∘ g^((L-1) % 5) ∘ σ
        g_factor = self._gp[(word_length - 1) % 5]
        self.base = perm_compose(self.base, perm_compose(g_factor, self.sigma))
        return pt

    def encrypt_word(self, pt_runes: list[int], word_length: int) -> list[int]:
        """Encrypt a single word and advance the base state."""
        ct = []
        for j, p in enumerate(pt_runes):
            c = self.base[self._gp[j % 5][p]]
            ct.append(c)
        g_factor = self._gp[(word_length - 1) % 5]
        self.base = perm_compose(self.base, perm_compose(g_factor, self.sigma))
        return ct

    def decrypt_corpus(self, ct_words: list[list[int]]) -> list[list[int]]:
        """Decrypt the full corpus; resets base state to current self.base."""
        # Save start state for reproducibility
        save_base = list(self.base)
        pt_words = []
        for w in ct_words:
            pt_words.append(self.decrypt_word(w, len(w)))
        self.base = save_base  # caller controls state lifetime
        return pt_words

    def encrypt_corpus(self, pt_words: list[list[int]]) -> list[list[int]]:
        save_base = list(self.base)
        ct_words = []
        for w in pt_words:
            ct_words.append(self.encrypt_word(w, len(w)))
        self.base = save_base
        return ct_words


# ============================================================================
# SELF-TEST
# ============================================================================
def _selftest() -> None:
    rng = random.Random(3301)
    g = random_order_5_permutation(rng)
    assert is_order_5(g), "random_order_5_permutation must produce order-5 g"
    sigma = list(range(M)); rng.shuffle(sigma)
    base0 = list(range(M)); rng.shuffle(base0)

    # Random plaintext corpus
    words = [[rng.randrange(M) for _ in range(rng.randint(1, 12))]
             for _ in range(500)]

    enc = LengthClockedWalk(base0, g, sigma)
    ct = enc.encrypt_corpus(words)
    dec = LengthClockedWalk(base0, g, sigma)
    rec = dec.decrypt_corpus(ct)
    assert rec == words, "round-trip failed"

    # Wrong key must NOT decrypt
    bad = base0[:]; bad[0], bad[1] = bad[1], bad[0]
    wrong = LengthClockedWalk(bad, g, sigma)
    assert wrong.decrypt_corpus(ct) != words, "wrong key decrypted (bug)"

    # Verify the "rare-diagonal" / order-5 property: g^5 = id exactly.
    assert perm_power(g, 5) == list(range(M)), "g^5 must be identity"

    print("Self-test OK:")
    print("  - perm_compose / perm_inverse / perm_power correct")
    print("  - is_order_5 detects order-5 permutations")
    print("  - random_order_5_permutation yields g^5 == identity")
    print("  - LengthClockedWalk encrypt_corpus / decrypt_corpus round-trip on 500 words")
    print("  - wrong base_0 fails to decrypt (cipher is sensitive to key)")
    print(f"  - g = {g}")
    print(f"  - g^5 == id? {is_order_5(g)}")


if __name__ == "__main__":
    _selftest()
