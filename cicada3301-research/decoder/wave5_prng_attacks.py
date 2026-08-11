#!/usr/bin/env python3
"""
wave5_prng_attacks.py — Wave-5: PRNG-seed-from-hash attacks on Cicada 3301's
unsolved Liber Primus pages.

Eight attacks (per task p2g):
  1. ChaCha20 keystream seeded by page-56 hash (3 key/nonce variants × 3 decrypt modes).
  2. AES-CTR keystream (3 key/IV variants × 3 decrypt modes).
  3. BLAKE2b XOF (3 seed variants × 3 decrypt modes).
  4. SHAKE256 XOF (3 seed variants × 3 decrypt modes).
  5. Hash-iteration keystream (SHA-512 chained, 8 seeds × 3 decrypt modes).
  6. RC4 keystream (3 key variants × 3 decrypt modes).
  7. Hash-as-checksum: SHA-512/BLAKE2b/etc of every prior-wave top plaintext.
  8. Dot-delimiter ASCII control-channel steganography.

Foundation: Wave-4 conclusion (WAVE4_ATTACK_RESULTS.md) — "cipher is most likely a
stream cipher seeded with the page-56 hash via a standard PRNG (ChaCha20/AES-CTR/
BLAKE2b-XOF/SHAKE256 — UNTESTED, top priority)".

Scoring reference (Wave-3 100k random-string control):
  mean=65.93, P99=74.36, P99.99=79.48, max=81.06.   Real English ≥ 110.
  => any score > 80 here is a potential break (highlighted).
"""
from __future__ import annotations
import os, sys, json, hashlib, time, struct, itertools
from typing import List, Dict, Tuple, Optional, Iterable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gematria_primus import (
    RUNES, N_RUNES, MOD, LETTERS, PRIMES,
    RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER,
    clean_runes, runes_to_decimals, decimals_to_runes,
    runes_to_latin, decimals_to_latin, english_score, DELIMITERS,
)

# Crypto libs
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("WARNING: cryptography library not available; ChaCha20/AES attacks will skip.")

# ============================================================================
# LOAD UNSOLVED CORPUS
# ============================================================================
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, 'unsolved_pages.json')) as f:
    UNSOLVED_PAGES = json.load(f)

UNSOLVED_FULL = "".join(clean_runes(p.get('runes', '')) for p in UNSOLVED_PAGES)
assert len(UNSOLVED_FULL) == 12956, f"Expected 12956 runes, got {len(UNSOLVED_FULL)}"

CT_DEC = runes_to_decimals(UNSOLVED_FULL)             # 12956 ints in [0,28]
SAMPLE_BOUNDARIES = [300, 1000]
NEEDED_LEN = len(CT_DEC)                              # 12956 bytes of keystream

# ============================================================================
# KEY CONSTANTS — page-56 hash + thematic seeds
# ============================================================================
PAGE56_HASH_HEX = (
    "36367763ab73783c7af284446c59466b4cd653239a311cb7116d4618dee09a8425"
    "893dc7500b464fdaf1672d7bef5e891c6e2274568926a49fb4f45132c2a8b4"
)
assert len(PAGE56_HASH_HEX) == 128
PAGE56_HASH_BYTES = bytes.fromhex(PAGE56_HASH_HEX)
assert len(PAGE56_HASH_BYTES) == 64

# Parable text (page 57, decoded English)
PARABLE_TEXT = "PARABLE LIKE THE INSTAR TUNNELING TO THE SURFACE WE MUST SHED OUR OWN CIRCUMFERENCES FIND THE DIVINITY WITHIN AND EMERGE"

# Thematic numeric seeds (as ASCII strings)
NUMERIC_SEEDS = {
    "1033":        b"1033",
    "3301":        b"3301",
    "761":         b"761",
    "11570":       b"11570",
    "1595277641":  b"1595277641",
    "hash_rev":    PAGE56_HASH_BYTES[::-1],
    "parable":     PARABLE_TEXT.encode("utf-8"),
    "page56_hash": PAGE56_HASH_BYTES,
}

# ============================================================================
# DECRYPT MODES
# ============================================================================
def decrypt_modes(ct_dec: List[int], ks: bytes) -> Dict[str, List[int]]:
    """Apply 3 decrypt rules; return {mode_name: plaintext_decs}.

      subtract_mod29      : pt[i] = (ct[i] - ks[i])           % 29
      xor_mod29           : pt[i] = (ct[i] XOR ks[i])         % 29
      subtract_byte_mod29 : pt[i] = (ct[i] - (ks[i] % 29))   % 29
    """
    n = min(len(ct_dec), len(ks))
    out = {"subtract_mod29": [], "xor_mod29": [], "subtract_byte_mod29": []}
    for i in range(n):
        c = ct_dec[i]
        b = ks[i]
        out["subtract_mod29"].append((c - b) % MOD)
        out["xor_mod29"].append((c ^ b) % MOD)
        out["subtract_byte_mod29"].append((c - (b % MOD)) % MOD)
    return out


def score_plaintext(pt_decs: List[int], boundaries=SAMPLE_BOUNDARIES) -> Dict[int, Dict]:
    """Score first N runes for each N in boundaries."""
    res = {}
    for n in boundaries:
        decs_n = pt_decs[:n]
        runes_n = decimals_to_runes(decs_n)
        latin_n = decimals_to_latin(decs_n, sep="")
        score = english_score(latin_n)
        res[n] = {
            "score": round(score, 3),
            "latin_preview": latin_n[:80],
            "runes_preview": runes_n[:40],
        }
    return res


# ============================================================================
# ATTACK 1 — ChaCha20 keystream
# ============================================================================
def attack1_chacha20() -> List[Dict]:
    """
    Variants:
      a) key = first 32 bytes of hash; nonce = 16 zero bytes.
      b) key = first 32 bytes of hash; nonce = last 16 bytes of hash (or bytes 32-44 if IETF).
      c) key = bytes 32-64 of hash; nonce = first 16 bytes of hash.
    """
    if not HAS_CRYPTO:
        return [{"attack": 1, "error": "cryptography library not available"}]
    results = []
    variants = [
        ("key=hash[0:32]  nonce=zeros16",
            PAGE56_HASH_BYTES[:32], b"\x00" * 16),
        ("key=hash[0:32]  nonce=hash[32:48]",
            PAGE56_HASH_BYTES[:32], PAGE56_HASH_BYTES[32:48]),
        ("key=hash[32:64] nonce=hash[0:16]",
            PAGE56_HASH_BYTES[32:64], PAGE56_HASH_BYTES[:16]),
        ("key=hash[0:32]  nonce=hash[48:64]",
            PAGE56_HASH_BYTES[:32], PAGE56_HASH_BYTES[48:64]),
    ]
    for label, key, nonce in variants:
        # ChaCha20 (cryptography lib uses 256-bit key, 16-byte nonce / 12-byte RFC7539 nonce)
        try:
            if len(nonce) == 16:
                algo = algorithms.ChaCha20(key, nonce)
            elif len(nonce) == 12:
                # Use IETF ChaCha20-Poly1305-style nonce? No, ChaCha20 here wants 16-byte.
                # Pad to 16.
                algo = algorithms.ChaCha20(key, nonce + b"\x00\x00\x00\x00")
            else:
                continue
            cipher = Cipher(algo, mode=None, backend=default_backend())
            enc = cipher.encryptor()
            ks = enc.update(b"\x00" * NEEDED_LEN) + enc.finalize()
        except Exception as e:
            results.append({"attack": 1, "variant": label, "error": str(e)})
            continue
        modes_res = decrypt_modes(CT_DEC, ks)
        for mode_name, pt_decs in modes_res.items():
            r = {
                "attack": 1, "cipher": "ChaCha20", "variant": label, "decrypt_mode": mode_name,
                "scores": score_plaintext(pt_decs),
                "ks_preview_hex": ks[:32].hex(),
            }
            r["top_score"] = max(r["scores"][n]["score"] for n in SAMPLE_BOUNDARIES)
            results.append(r)
    return results


# ============================================================================
# ATTACK 2 — AES-CTR keystream
# ============================================================================
def attack2_aes_ctr() -> List[Dict]:
    """
    Variants:
      a) AES-128: key=hash[0:16], IV=hash[16:32] (full 16-byte IV/counter).
      b) AES-256: key=hash[0:32], nonce=hash[32:44] (12-byte nonce, 4-byte counter zero).
      c) AES-256: key=hash[32:64], IV=hash[0:16].
    """
    if not HAS_CRYPTO:
        return [{"attack": 2, "error": "cryptography library not available"}]
    results = []
    variants = [
        ("AES128  key=hash[0:16]  IV=hash[16:32]",
            PAGE56_HASH_BYTES[:16], PAGE56_HASH_BYTES[16:32]),
        ("AES256  key=hash[0:32]  nonce=hash[32:44]+ctr0",
            PAGE56_HASH_BYTES[:32], PAGE56_HASH_BYTES[32:44] + b"\x00\x00\x00\x00"),
        ("AES256  key=hash[32:64] IV=hash[0:16]",
            PAGE56_HASH_BYTES[32:64], PAGE56_HASH_BYTES[:16]),
        ("AES128  key=hash[32:48] IV=hash[48:64]",
            PAGE56_HASH_BYTES[32:48], PAGE56_HASH_BYTES[48:64]),
    ]
    for label, key, iv in variants:
        try:
            cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
            enc = cipher.encryptor()
            ks = enc.update(b"\x00" * NEEDED_LEN) + enc.finalize()
        except Exception as e:
            results.append({"attack": 2, "variant": label, "error": str(e)})
            continue
        modes_res = decrypt_modes(CT_DEC, ks)
        for mode_name, pt_decs in modes_res.items():
            r = {
                "attack": 2, "cipher": "AES-CTR", "variant": label, "decrypt_mode": mode_name,
                "scores": score_plaintext(pt_decs),
                "ks_preview_hex": ks[:32].hex(),
            }
            r["top_score"] = max(r["scores"][n]["score"] for n in SAMPLE_BOUNDARIES)
            results.append(r)
    return results


# ============================================================================
# ATTACK 3 — BLAKE2b XOF
# ============================================================================
def blake2b_xof(seed: bytes, length: int, salt: bytes = b"", personal: bytes = b"") -> bytes:
    """Generate `length` bytes of BLAKE2b output by chaining 64-byte blocks.
    Block[i] = blake2b(seed || counter_be64(i) || prev_block, digest_size=64, salt, personal).
    """
    out = b""
    i = 0
    prev = b""
    while len(out) < length:
        h = hashlib.blake2b(digest_size=64)
        h.update(seed)
        h.update(struct.pack(">Q", i))
        if prev:
            h.update(prev)
        if salt:
            h.update(salt)
        if personal:
            h.update(personal)
        block = h.digest()
        out += block
        prev = block
        i += 1
    return out[:length]


def attack3_blake2b() -> List[Dict]:
    """
    Variants:
      a) seed = full 64-byte hash, no salt/personal.
      b) seed = full 64-byte hash AS personalisation, with empty seed.
      c) seed = full 64-byte hash AS salt, with empty seed.
      d) seed = first 32 bytes of hash.
    """
    results = []
    variants = [
        ("seed=full_hash(64B)",            PAGE56_HASH_BYTES, b"", b""),
        ("personal=full_hash(64B→trunc32B)", b"",               b"", PAGE56_HASH_BYTES[:32]),
        ("salt=full_hash(64B→trunc32B)",    b"",               PAGE56_HASH_BYTES[:32], b""),
        ("seed=hash[0:32]",                PAGE56_HASH_BYTES[:32], b"", b""),
    ]
    for label, seed, salt, personal in variants:
        try:
            ks = blake2b_xof(seed, NEEDED_LEN, salt=salt, personal=personal)
        except Exception as e:
            results.append({"attack": 3, "variant": label, "error": str(e)})
            continue
        modes_res = decrypt_modes(CT_DEC, ks)
        for mode_name, pt_decs in modes_res.items():
            r = {
                "attack": 3, "cipher": "BLAKE2b-XOF", "variant": label, "decrypt_mode": mode_name,
                "scores": score_plaintext(pt_decs),
                "ks_preview_hex": ks[:32].hex(),
            }
            r["top_score"] = max(r["scores"][n]["score"] for n in SAMPLE_BOUNDARIES)
            results.append(r)
    return results


# ============================================================================
# ATTACK 4 — SHAKE256 XOF
# ============================================================================
def attack4_shake256() -> List[Dict]:
    """
    Variants:
      a) seed = full 64-byte hash.
      b) seed = first 32 bytes of hash.
      c) seed = full hash reversed.
      d) seed = SHAKE256(hash, 64) (double-XOF).
    """
    results = []
    seeds = [
        ("seed=full_hash(64B)",         PAGE56_HASH_BYTES),
        ("seed=hash[0:32]",             PAGE56_HASH_BYTES[:32]),
        ("seed=hash_reversed",          PAGE56_HASH_BYTES[::-1]),
        ("seed=shake256(hash,64)",      hashlib.shake_256(PAGE56_HASH_BYTES).digest(64)),
    ]
    for label, seed in seeds:
        try:
            ks = hashlib.shake_256(seed).digest(NEEDED_LEN)
        except Exception as e:
            results.append({"attack": 4, "variant": label, "error": str(e)})
            continue
        modes_res = decrypt_modes(CT_DEC, ks)
        for mode_name, pt_decs in modes_res.items():
            r = {
                "attack": 4, "cipher": "SHAKE256-XOF", "variant": label, "decrypt_mode": mode_name,
                "scores": score_plaintext(pt_decs),
                "ks_preview_hex": ks[:32].hex(),
            }
            r["top_score"] = max(r["scores"][n]["score"] for n in SAMPLE_BOUNDARIES)
            results.append(r)
    return results


# ============================================================================
# ATTACK 5 — Hash-iteration keystream (SHA-512 chained)
# ============================================================================
def hash_iteration_keystream(seed: bytes, length: int, algo: str = "sha512") -> bytes:
    """keystream = H(seed) || H(H(seed)) || H(H(H(seed))) || ...
    Each block is algo_digest_size bytes (64 for SHA-512).
    """
    out = b""
    state = seed
    while len(out) < length:
        state = hashlib.new(algo, state).digest()
        out += state
    return out[:length]


def attack5_hash_iteration() -> List[Dict]:
    """
    8 seeds × 3 decrypt modes. Algo = SHA-512.
    Seeds: page56_hash (bytes), "1033", "3301", "761", "11570", "1595277641", parable, hash_rev.
    """
    results = []
    for label, seed in NUMERIC_SEEDS.items():
        ks = hash_iteration_keystream(seed, NEEDED_LEN, algo="sha512")
        modes_res = decrypt_modes(CT_DEC, ks)
        for mode_name, pt_decs in modes_res.items():
            r = {
                "attack": 5, "cipher": "SHA512-iter", "seed": label, "decrypt_mode": mode_name,
                "scores": score_plaintext(pt_decs),
                "ks_preview_hex": ks[:32].hex(),
            }
            r["top_score"] = max(r["scores"][n]["score"] for n in SAMPLE_BOUNDARIES)
            results.append(r)
    # Bonus: also test SHAKE-style iteration (different)
    return results


# ============================================================================
# ATTACK 6 — RC4 keystream (pure Python)
# ============================================================================
def rc4_keystream(key: bytes, length: int) -> bytes:
    """Pure-Python RC4."""
    S = list(range(256))
    j = 0
    keylen = len(key)
    for i in range(256):
        j = (j + S[i] + key[i % keylen]) & 0xFF
        S[i], S[j] = S[j], S[i]
    out = bytearray()
    i = j = 0
    for _ in range(length):
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out.append(S[(S[i] + S[j]) & 0xFF])
    return bytes(out)


def attack6_rc4() -> List[Dict]:
    """
    Variants:
      a) key = full 64-byte hash.
      b) key = first 32 bytes.
      c) key = first 16 bytes.
      d) key = first 8 bytes (RC4 typical).
    """
    results = []
    variants = [
        ("key=full_hash(64B)", PAGE56_HASH_BYTES),
        ("key=hash[0:32]",    PAGE56_HASH_BYTES[:32]),
        ("key=hash[0:16]",    PAGE56_HASH_BYTES[:16]),
        ("key=hash[0:8]",     PAGE56_HASH_BYTES[:8]),
    ]
    for label, key in variants:
        ks = rc4_keystream(key, NEEDED_LEN)
        modes_res = decrypt_modes(CT_DEC, ks)
        for mode_name, pt_decs in modes_res.items():
            r = {
                "attack": 6, "cipher": "RC4", "variant": label, "decrypt_mode": mode_name,
                "scores": score_plaintext(pt_decs),
                "ks_preview_hex": ks[:32].hex(),
            }
            r["top_score"] = max(r["scores"][n]["score"] for n in SAMPLE_BOUNDARIES)
            results.append(r)
    return results


# ============================================================================
# ATTACK 7 — Hash-as-checksum verification
# ============================================================================
def gather_prior_candidates() -> List[Dict]:
    """Pull top plaintext candidates from wave-2/3/4 result JSONs."""
    cands = []
    # Wave-4 attack2 (hill-climb best)
    try:
        d = json.load(open(os.path.join(HERE, 'wave4_attack2_results.json')))
        for combo_id, info in d.get('best_per_combo', {}).items():
            preview = info.get('best_pt_preview', '')
            if preview:
                cands.append({
                    "source": "wave4_attack2",
                    "combo": combo_id,
                    "score": info.get('best_score'),
                    "preview": preview,
                })
        ob = d.get('overall_best', {})
        if ob.get('best_pt_preview'):
            cands.append({
                "source": "wave4_attack2_overall",
                "combo": f"L{ob.get('L')}_{ob.get('mode')}",
                "score": ob.get('best_score'),
                "preview": ob.get('best_pt_preview'),
            })
    except Exception as e:
        print(f"  (warn) wave4_attack2 load: {e}")
    # Wave-4 attack1/3/4 variants
    try:
        d = json.load(open(os.path.join(HERE, 'wave4_attacks_134.json')))
        for atk_key in ['attack1', 'attack3', 'attack4']:
            atk = d.get(atk_key, {})
            for v in atk.get('variants', []):
                label = v.get('variant', v.get('label', '?'))
                for samp_key in ['s300', 's1000']:
                    if samp_key in v:
                        s = v[samp_key]
                        prev = s.get('best_latin_preview') or s.get('key_preview') or ""
                        if prev:
                            cands.append({
                                "source": f"wave4_{atk_key}",
                                "combo": f"{label}_{samp_key}",
                                "score": s.get('best_score'),
                                "preview": prev,
                            })
    except Exception as e:
        print(f"  (warn) wave4_attacks_134 load: {e}")
    # Wave-2 / wave-3 — search recursively for any latin-preview fields
    for fname in ['wave3_attack_results.json', 'wave2_attack_results.json']:
        try:
            d = json.load(open(os.path.join(HERE, fname)))
            def walk(obj, path=''):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, dict) and ('best_latin_preview' in v or 'latin_preview' in v or 'plaintext' in v):
                            prev = v.get('best_latin_preview') or v.get('latin_preview') or v.get('plaintext', '')
                            sc = v.get('best_score') or v.get('score')
                            if prev:
                                cands.append({
                                    "source": fname,
                                    "combo": f"{path}/{k}",
                                    "score": sc,
                                    "preview": prev[:200],
                                })
                        walk(v, path + "/" + k)
                elif isinstance(obj, list):
                    for i, v in enumerate(obj):
                        walk(v, f"{path}[{i}]")
            walk(d)
        except Exception as e:
            print(f"  (warn) {fname} load: {e}")
    return cands


def attack7_hash_checksum() -> Dict:
    """For each prior candidate, hash the plaintext in multiple encodings and
    compare to the page-56 hash (full 64 bytes) AND its sub-prefixes (32B, 16B)."""
    cands = gather_prior_candidates()
    hashes_to_check = {
        "sha512":         lambda b: hashlib.sha512(b).digest(),
        "sha512_prefix32":lambda b: hashlib.sha512(b).digest()[:32],
        "sha256":         lambda b: hashlib.sha256(b).digest(),
        "sha1":           lambda b: hashlib.sha1(b).digest(),
        "blake2b":        lambda b: hashlib.blake2b(b, digest_size=64).digest(),
        "blake2b_32":     lambda b: hashlib.blake2b(b, digest_size=32).digest(),
        "blake2s":        lambda b: hashlib.blake2s(b, digest_size=32).digest(),
        "sha3_512":       lambda b: hashlib.sha3_512(b).digest(),
        "shake256_64":    lambda b: hashlib.shake_256(b).digest(64),
        "shake256_32":    lambda b: hashlib.shake_256(b).digest(32),
    }
    target_full = PAGE56_HASH_BYTES
    target_prefix32 = PAGE56_HASH_BYTES[:32]
    target_prefix16 = PAGE56_HASH_BYTES[:16]
    target_prefix8  = PAGE56_HASH_BYTES[:8]
    encodings = {
        "latin_str":     lambda p: p.encode("utf-8", errors="replace"),
        "latin_lower":    lambda p: p.lower().encode("utf-8", errors="replace"),
        "latin_upper":    lambda p: p.upper().encode("utf-8", errors="replace"),
        "latin_no_space": lambda p: p.replace(" ", "").encode("utf-8", errors="replace"),
        "dec_mod256":     lambda p: bytes(c % 256 for c in p.encode("utf-8", errors="replace")),
    }
    matches = []
    n_tested = 0
    for cand in cands:
        prev = cand.get('preview', '')
        if not prev:
            continue
        for enc_name, enc_fn in encodings.items():
            try:
                pt_bytes = enc_fn(prev)
            except Exception:
                continue
            for h_name, h_fn in hashes_to_check.items():
                try:
                    digest = h_fn(pt_bytes)
                except Exception:
                    continue
                n_tested += 1
                # Compare to all target prefixes
                if digest == target_full:
                    matches.append({"candidate": cand, "encoding": enc_name, "hash": h_name, "match": "FULL_64B"})
                elif len(digest) >= 32 and digest[:32] == target_prefix32 and h_name not in ("sha1","sha256","blake2s","blake2b_32","shake256_32"):
                    matches.append({"candidate": cand, "encoding": enc_name, "hash": h_name, "match": "PREFIX_32B"})
                elif len(digest) >= 16 and digest[:16] == target_prefix16:
                    matches.append({"candidate": cand, "encoding": enc_name, "hash": h_name, "match": "PREFIX_16B"})
                elif len(digest) >= 8 and digest[:8] == target_prefix8:
                    matches.append({"candidate": cand, "encoding": enc_name, "hash": h_name, "match": "PREFIX_8B"})
    return {"n_candidates": len(cands), "n_hashes_tested": n_tested, "matches": matches, "sample_candidates": cands[:5]}


# ============================================================================
# ATTACK 8 — Dot-delimiter ASCII control channel
# ============================================================================
DELIM_TO_CTRL: Dict[str, int] = {
    "\n": 0x0A,  # LF
    "\r": 0x0D,  # CR
    "/":  0x2F,  # solidus (not really ctrl, but used as delim)
    "•":  0x0A,  # bullet -> LF (CicadaSolvers hint)
    "·":  0x0A,  # middle dot -> LF
    ".":  0x0D,  # period -> CR
    "-":  0x17,  # hyphen -> ETB
    "_":  0x17,
    "=":  0x17,
    "*":  0x17,
    "%":  0x17,
    "&":  0x17,
    "$":  0x17,
    "#":  0x17,
}


def extract_delimiter_channel() -> Tuple[bytes, Dict]:
    """Walk each page's raw_section; for every delimiter between/around runes,
    record the corresponding ASCII control byte. Returns (bytes, meta)."""
    out = bytearray()
    counts: Dict[str, int] = {}
    delim_seq_per_page = []
    for p in UNSOLVED_PAGES:
        rs = p.get('raw_section', '')
        page_seq = []
        for ch in rs:
            if ch in DELIMITERS and ch not in (" ", "\t"):
                ctrl = DELIM_TO_CTRL.get(ch, None)
                if ctrl is not None:
                    page_seq.append(ctrl)
                    counts[ch] = counts.get(ch, 0) + 1
                    out.append(ctrl)
        delim_seq_per_page.append({"page_id": p.get('page_id'), "n_delims": len(page_seq)})
    return bytes(out), {"counts": counts, "total_delims": len(out), "per_page": delim_seq_per_page}


def attack8_delimiter_channel() -> Dict:
    """Use delimiter byte-stream as keystream over the rune-decimals."""
    dstream, meta = extract_delimiter_channel()
    results = {"meta": meta, "dstream_hex_preview": dstream[:32].hex()}
    # Check if delimiter stream itself looks meaningful
    results["dstream_as_text"] = dstream[:200].decode("latin-1", errors="replace")

    # If dstream has >=1 byte per rune, we can use first len(CT_DEC) bytes
    usable = dstream[:NEEDED_LEN]
    if len(usable) < NEEDED_LEN:
        # pad with 0x0A (LF)
        usable = usable + b"\x0a" * (NEEDED_LEN - len(usable))
    # Apply 3 decrypt modes against rune-decimals
    modes_res = decrypt_modes(CT_DEC, usable)
    scored = {}
    for mode_name, pt_decs in modes_res.items():
        scored[mode_name] = score_plaintext(pt_decs)
    results["decrypt_scores"] = scored

    # ALSO: test the delimiter stream AS a hash/URL/etc by direct comparison
    results["dstream_len"] = len(dstream)
    # Compare delimiter stream hash to known Cicada hashes
    ds_hash = hashlib.sha512(dstream).hexdigest()
    results["dstream_sha512_prefix"] = ds_hash[:64]
    results["dstream_sha512_matches_page56"] = (
        dstream == PAGE56_HASH_BYTES or hashlib.sha512(dstream).digest() == PAGE56_HASH_BYTES
    )
    # Check if delimiter stream CONTAINS the page-56 hash bytes as a subsequence
    if PAGE56_HASH_BYTES in dstream:
        results["dstream_contains_hash"] = True
    else:
        results["dstream_contains_hash"] = False

    # Count distinct control-char distribution
    from collections import Counter
    cc = Counter(dstream)
    results["byte_distribution"] = {hex(b): c for b, c in cc.most_common(10)}

    return results


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 78)
    print("WAVE-5 PRNG-SEED-FROM-HASH ATTACKS — Cicada 3301 Liber Primus")
    print("=" * 78)
    print(f"Ciphertext: {len(CT_DEC)} runes (= {len(UNSOLVED_FULL)} chars).")
    print(f"Page-56 hash: {PAGE56_HASH_HEX[:32]}... ({len(PAGE56_HASH_BYTES)} bytes)")
    print(f"Noise band: mean=65.93, P99=74.36, P99.99=79.48, max=81.06. Real English ≥ 110.")
    print(f"cryptography library: {'available' if HAS_CRYPTO else 'NOT available'}")
    print()

    all_results = {}
    t0 = time.time()
    print("[*] Attack 1 — ChaCha20 keystream...")
    all_results["attack1_chacha20"] = attack1_chacha20()
    print(f"    {len(all_results['attack1_chacha20'])} results in {time.time()-t0:.1f}s")

    t1 = time.time()
    print("[*] Attack 2 — AES-CTR keystream...")
    all_results["attack2_aes_ctr"] = attack2_aes_ctr()
    print(f"    {len(all_results['attack2_aes_ctr'])} results in {time.time()-t1:.1f}s")

    t2 = time.time()
    print("[*] Attack 3 — BLAKE2b XOF...")
    all_results["attack3_blake2b"] = attack3_blake2b()
    print(f"    {len(all_results['attack3_blake2b'])} results in {time.time()-t2:.1f}s")

    t3 = time.time()
    print("[*] Attack 4 — SHAKE256 XOF...")
    all_results["attack4_shake256"] = attack4_shake256()
    print(f"    {len(all_results['attack4_shake256'])} results in {time.time()-t3:.1f}s")

    t4 = time.time()
    print("[*] Attack 5 — Hash-iteration (SHA-512 chained, 8 seeds)...")
    all_results["attack5_hash_iteration"] = attack5_hash_iteration()
    print(f"    {len(all_results['attack5_hash_iteration'])} results in {time.time()-t4:.1f}s")

    t5 = time.time()
    print("[*] Attack 6 — RC4 keystream...")
    all_results["attack6_rc4"] = attack6_rc4()
    print(f"    {len(all_results['attack6_rc4'])} results in {time.time()-t5:.1f}s")

    t6 = time.time()
    print("[*] Attack 7 — Hash-as-checksum on prior-wave candidates...")
    all_results["attack7_hash_checksum"] = attack7_hash_checksum()
    print(f"    Tested {all_results['attack7_hash_checksum']['n_hashes_tested']} hashes "
          f"over {all_results['attack7_hash_checksum']['n_candidates']} candidates in {time.time()-t6:.1f}s")
    print(f"    Matches: {len(all_results['attack7_hash_checksum']['matches'])}")

    t7 = time.time()
    print("[*] Attack 8 — Dot-delimiter ASCII control-channel...")
    all_results["attack8_delim_channel"] = attack8_delimiter_channel()
    print(f"    Delimiter stream: {all_results['attack8_delim_channel']['dstream_len']} bytes in {time.time()-t7:.1f}s")
    print(f"    Byte distribution: {all_results['attack8_delim_channel']['byte_distribution']}")

    # Summary
    print()
    print("=" * 78)
    print("SUMMARY — Top scores per attack (noise band: P99=74.36, max=81.06)")
    print("=" * 78)
    overall_top = []
    for atk_name in ["attack1_chacha20", "attack2_aes_ctr", "attack3_blake2b",
                      "attack4_shake256", "attack5_hash_iteration", "attack6_rc4"]:
        res = all_results[atk_name]
        if isinstance(res, list) and res and "error" not in res[0]:
            top = sorted(res, key=lambda r: r.get("top_score", 0), reverse=True)[:3]
            print(f"\n  {atk_name} — top 3:")
            for r in top:
                tag = " *** POTENTIAL BREAK ***" if r["top_score"] > 80 else ""
                print(f"    [{r['top_score']:6.2f}] {r['cipher']:14s} | {r.get('variant', r.get('seed',''))[:50]:50s} | {r['decrypt_mode']:22s}{tag}")
                print(f"             s300: {r['scores'][300]['latin_preview']}")
                print(f"             s1000: {r['scores'][1000]['latin_preview']}")
            for r in top:
                overall_top.append((atk_name, r))
        else:
            print(f"\n  {atk_name} — error or empty: {res[0] if res else 'no results'}")

    # Global top 10
    print()
    print("=" * 78)
    print("GLOBAL TOP 10 (across Attacks 1-6):")
    print("=" * 78)
    overall_top.sort(key=lambda x: x[1]["top_score"], reverse=True)
    for i, (atk_name, r) in enumerate(overall_top[:10], 1):
        tag = " *** POTENTIAL BREAK ***" if r["top_score"] > 80 else ""
        print(f"  {i:2d}. [{r['top_score']:6.2f}] {atk_name:24s} | {r['cipher']:14s} | "
              f"{r.get('variant', r.get('seed',''))[:40]:40s} | {r['decrypt_mode']}{tag}")

    # Save JSON
    out_path = os.path.join(HERE, 'wave5_prng_results.json')
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[+] Results saved to {out_path}")
    return all_results


if __name__ == "__main__":
    main()
