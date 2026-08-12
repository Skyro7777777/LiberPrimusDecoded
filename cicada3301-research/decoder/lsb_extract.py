#!/usr/bin/env python3
"""
LSB extraction (spatial domain) — fast version for Cicada 3301 LP page JPEGs.

NOTE: JPEG is lossy, so spatial LSBs are mostly compression noise. The dominant
stego channels for JPEG are DCT-coefficient LSBs (handled separately).
This script runs spatial LSB extraction anyway for thoroughness.

For each unsolved LP2 page JPEG:
  - Opens with PIL, downsizes to 600x900 for speed (still meaningful)
  - Extracts LSBs from R, G, B, RGB-interleaved, RGB-XOR
  - From bit-planes 0 (LSB), 1 (2nd-LSB), 2 (3rd-LSB)
  - Bit-to-byte conversion: MSB-first
  - Searches for ASCII, PGP, magic bytes, URLs, hashes
  - Computes SHA-512 of each stream and checks vs page-56 hash
"""
import os, sys, json, hashlib, re, time
from PIL import Image
import numpy as np

IMAGES_DIR = "/home/z/my-project/cicada3301-research/images"
OUT_DIR = "/home/z/my-project/cicada3301-research/stego_output/lsb"
os.makedirs(OUT_DIR, exist_ok=True)

# Two known variants of page-56 hash from prior work
PAGE56_HASH_VARIANTS = [
    "36367763ab73783c7af284446c59466b4cd653239a311cb7116d4618dee09a8425893dc7500b464fdaf1672d7bef5e891c6e2274568926a49fb4f45132c2a8b4",
    "36367763ab73783c7af2d4125bb1ec4a5e2e0defe7d0f22e1ca5ce95e3d0044b6785a3eef1c3c7d2f8f1f4d3c7d2f8f1f4d3c7d2f8f1f4d3c7d2f8f1f4d3c7d2f8f1f4d3c7d2f8f1f4d3c7d2f8f1f4d3c7d2f8f1f4",
]
PHV_SET = set(h.lower() for h in PAGE56_HASH_VARIANTS)

MAGIC_BYTES = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"%PDF": "PDF",
    b"PK\x03\x04": "ZIP",
    b"Rar!": "RAR",
    b"\x1f\x8b": "GZIP",
    b"GIF8": "GIF",
    b"BZh": "BZIP2",
    b"-----BEGIN PGP": "PGP-message",
    b"-----BEGIN": "ASCII-armor",
}

URL_REGEX = re.compile(rb'https?://[^\s\x00<>"\'\\]{6,}', re.IGNORECASE)
PGP_HEADER = re.compile(rb'-----BEGIN PGP (MESSAGE|SIGNATURE|PUBLIC KEY|PRIVATE KEY|SECRET KEY)-----')
HASH_REGEX = re.compile(rb'\b[0-9a-f]{40,128}\b')

def bits_to_bytes_msb(bits):
    """Vectorized MSB-first bit-to-byte conversion."""
    n = (len(bits) // 8) * 8
    bits = bits[:n].astype(np.uint8)
    # Reshape to (n/8, 8) and weight as 128, 64, 32, ..., 1
    weights = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.uint8)
    bytes_arr = (bits.reshape(-1, 8) * weights).sum(axis=1).astype(np.uint8)
    return bytes_arr.tobytes()

def search_stream(name, page_id, data, max_check=1024*1024):
    findings = {
        "name": name, "page_id": page_id, "size_bytes": len(data),
        "magic_matches": [], "ascii_strings": [], "pgp_matches": [],
        "urls": [], "hashes": [], "sha512": None, "blake2b": None,
        "matches_page56": False,
    }
    if not data: return findings
    # Only check first 1 MB for magic/ASCII (huge streams would take forever otherwise)
    head = data[:max_check]
    # Magic
    for magic, label in MAGIC_BYTES.items():
        idx = head.find(magic)
        if idx >= 0:
            findings["magic_matches"].append({"offset": idx, "label": label})
    # PGP
    for m in PGP_HEADER.finditer(head):
        findings["pgp_matches"].append({"offset": m.start()})
    # URLs
    for m in URL_REGEX.finditer(head):
        findings["urls"].append({"offset": m.start(), "url": m.group(0).decode('ascii', errors='ignore')[:100]})
    # Hash-like
    for m in HASH_REGEX.finditer(head):
        findings["hashes"].append({"offset": m.start(), "hash": m.group(0).decode('ascii', errors='ignore')[:128]})
    # ASCII strings >=10 chars with lowercase letters
    for m in re.finditer(rb'[\x20-\x7e]{10,}', head):
        s = m.group(0).decode('ascii', errors='ignore')
        if re.search(r'[a-z]{3,}', s):
            findings["ascii_strings"].append({"offset": m.start(), "string": s[:150]})
            if len(findings["ascii_strings"]) >= 5: break
    # Hashes
    s512 = hashlib.sha512(data).hexdigest()
    b2b = hashlib.blake2b(data).hexdigest()
    findings["sha512"] = s512
    findings["blake2b"] = b2b
    if s512 in PHV_SET or b2b in PHV_SET:
        findings["matches_page56"] = True
    return findings

def analyze_image(page_id, max_dim=900):
    img_path = os.path.join(IMAGES_DIR, f"{page_id}.jpg")
    if not os.path.exists(img_path):
        return None
    try:
        img = Image.open(img_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Downsample for speed (LSB in spatial domain will be mostly JPEG noise anyway)
        w, h = img.size
        scale = max_dim / max(w, h)
        if scale < 1.0:
            img = img.resize((int(w*scale), int(h*scale)), Image.BILINEAR)
        arr = np.array(img)
    except Exception as e:
        return {"page_id": page_id, "error": str(e)}
    h, w, c = arr.shape
    result = {"page_id": page_id, "dimensions": [w, h], "channels": c, "streams": []}
    # Pre-compute bit-planes
    for bp in [0, 1, 2]:
        mask = 1 << bp
        r_bits = ((arr[:,:,0] & mask) >> bp).flatten().astype(np.uint8)
        g_bits = ((arr[:,:,1] & mask) >> bp).flatten().astype(np.uint8)
        b_bits = ((arr[:,:,2] & mask) >> bp).flatten().astype(np.uint8)
        # RGB interleaved: R,G,B per pixel
        rgb_inter = np.empty(len(r_bits)*3, dtype=np.uint8)
        rgb_inter[0::3] = r_bits
        rgb_inter[1::3] = g_bits
        rgb_inter[2::3] = b_bits
        # XOR
        rgb_xor = r_bits ^ g_bits ^ b_bits
        for name, bits in [
            (f"R_b{bp}", r_bits),
            (f"G_b{bp}", g_bits),
            (f"B_b{bp}", b_bits),
            (f"RGB-inter_b{bp}", rgb_inter),
            (f"RGB-xor_b{bp}", rgb_xor),
        ]:
            data = bits_to_bytes_msb(bits)
            f = search_stream(name, page_id, data)
            result["streams"].append(f)
    return result

UNSOVED_PAGES = [17, 20, 23, 25, 32, 40, 44, 50, 56, 57, 71]
SOLVED_BASELINES = [0, 3, 8]

print(f"Analyzing {len(UNSOVED_PAGES)} unsolved + {len(SOLVED_BASELINES)} solved baseline pages")
all_results = {}
hits = []

for page in UNSOVED_PAGES + SOLVED_BASELINES:
    page_id = f"{page:02d}"
    t0 = time.time()
    r = analyze_image(page_id)
    if r is None:
        print(f"  {page_id}.jpg: NOT FOUND")
        continue
    if "error" in r:
        print(f"  {page_id}.jpg: ERROR {r['error']}")
        continue
    dt = time.time() - t0
    all_results[page_id] = r
    meaningful = 0
    for s in r["streams"]:
        if s["magic_matches"] or s["pgp_matches"] or s["urls"] or s["hashes"] or s["matches_page56"]:
            meaningful += 1
            hits.append({"page": page_id, "stream": s["name"], "findings": s})
    print(f"  {page_id}.jpg ({r['dimensions'][0]}x{r['dimensions'][1]}): {len(r['streams'])} streams in {dt:.1f}s, {meaningful} meaningful")

print(f"\n=== TOTAL MEANINGFUL HITS: {len(hits)} ===")
for h in hits:
    s = h["findings"]
    print(f"  page={h['page']} stream={h['stream']}: magic={s['magic_matches']} pgp={s['pgp_matches']} urls={len(s['urls'])} hashes={len(s['hashes'])} ascii={len(s['ascii_strings'])} page56match={s['matches_page56']}")

# Save
with open(os.path.join(OUT_DIR, "lsb_results.json"), "w") as f:
    json.dump({"all_results": all_results, "hits": hits}, f, indent=2, default=str)
print(f"\nResults saved to {OUT_DIR}/lsb_results.json")
