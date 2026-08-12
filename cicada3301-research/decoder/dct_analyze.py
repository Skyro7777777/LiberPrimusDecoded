#!/usr/bin/env python3
"""
JPEG DCT coefficient analysis for Cicada 3301 Liber Primus pages.

For each unsolved LP2 page JPEG:
  - Extract DCT coefficients via jpeglib
  - Examine LSBs of DCT coefficients (the JSteg/Outguess/F5 stego channel)
  - Look for patterns, magic bytes, ASCII, PGP, URLs, hashes
  - Compute SHA-512/BLAKE2b of DCT-LSB stream and check vs page-56 hash
"""
import os, sys, json, hashlib, re, time
import numpy as np

IMAGES_DIR = "/home/z/my-project/cicada3301-research/images"
OUT_DIR = "/home/z/my-project/cicada3301-research/stego_output/dct"
os.makedirs(OUT_DIR, exist_ok=True)

PAGE56_HASH_VARIANTS = [
    "36367763ab73783c7af284446c59466b4cd653239a311cb7116d4618dee09a8425893dc7500b464fdaf1672d7bef5e891c6e2274568926a49fb4f45132c2a8b4",
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
    if n == 0:
        return b''
    bits = bits[:n].astype(np.uint8)
    weights = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.uint8)
    bytes_arr = (bits.reshape(-1, 8) * weights).sum(axis=1).astype(np.uint8)
    return bytes_arr.tobytes()

def search_stream(name, page_id, data, max_check=2*1024*1024):
    findings = {
        "name": name, "page_id": page_id, "size_bytes": len(data),
        "magic_matches": [], "ascii_strings": [], "pgp_matches": [],
        "urls": [], "hashes": [], "sha512": None, "blake2b": None,
        "matches_page56": False, "preview": "",
    }
    if not data: return findings
    head = data[:max_check]
    for magic, label in MAGIC_BYTES.items():
        idx = head.find(magic)
        if idx >= 0:
            findings["magic_matches"].append({"offset": idx, "label": label})
    for m in PGP_HEADER.finditer(head):
        findings["pgp_matches"].append({"offset": m.start()})
    for m in URL_REGEX.finditer(head):
        findings["urls"].append({"offset": m.start(), "url": m.group(0).decode('ascii', errors='ignore')[:100]})
    for m in HASH_REGEX.finditer(head):
        findings["hashes"].append({"offset": m.start(), "hash": m.group(0).decode('ascii', errors='ignore')[:128]})
    for m in re.finditer(rb'[\x20-\x7e]{10,}', head):
        s = m.group(0).decode('ascii', errors='ignore')
        if re.search(r'[a-z]{3,}', s):
            findings["ascii_strings"].append({"offset": m.start(), "string": s[:150]})
            if len(findings["ascii_strings"]) >= 5: break
    s512 = hashlib.sha512(data).hexdigest()
    b2b = hashlib.blake2b(data).hexdigest()
    findings["sha512"] = s512
    findings["blake2b"] = b2b
    findings["preview"] = data[:32].hex()
    if s512 in PHV_SET or b2b in PHV_SET:
        findings["matches_page56"] = True
    return findings

def analyze_dct(page_id):
    """Extract DCT coefficients and analyze LSBs."""
    img_path = os.path.join(IMAGES_DIR, f"{page_id}.jpg")
    if not os.path.exists(img_path):
        return None
    try:
        import jpeglib
        # Read DCT coefficients
        img = jpeglib.read_dct(img_path)
        # Y, Cb, Cr DCT coefficient blocks; each block is 8x8
        # Compose a single coefficient stream from Y channel (largest)
        y_dct = img.Y  # shape: (n_blocks_vertical, n_blocks_horizontal, 8, 8)
        cb_dct = img.Cb
        cr_dct = img.Cr
    except Exception as e:
        return {"page_id": page_id, "error": f"DCT extraction failed: {e}"}
    
    result = {
        "page_id": page_id,
        "y_shape": list(y_dct.shape),
        "cb_shape": list(cb_dct.shape),
        "cr_shape": list(cr_dct.shape),
        "streams": [],
    }
    
    # Flatten and analyze each channel
    for ch_name, ch_data in [("Y", y_dct), ("Cb", cb_dct), ("Cr", cr_dct)]:
        flat = ch_data.flatten()
        # Convert signed int to unsigned for bit extraction
        # DCT coefficients range roughly -1024..1023
        # Strategy 1: LSB of absolute value
        abs_flat = np.abs(flat).astype(np.int64)
        # Strategy 2: LSB of (coeff + 1024) (offset to make unsigned)
        off_flat = (flat.astype(np.int64) + 1024).astype(np.uint64)
        # Strategy 3: bits of low byte of (coeff + 1024)
        low_byte = (off_flat & 0xFF).astype(np.uint8)
        # Strategy 4: parity (sign-XOR LSB)
        parity = (abs_flat & 1) ^ (flat < 0).astype(np.int64)
        
        for variant_name, bits_data in [
            (f"{ch_name}_abs_LSB", abs_flat & 1),
            (f"{ch_name}_offset_LSB", off_flat & 1),
            (f"{ch_name}_low_byte_bits", low_byte),  # 8 bits per coefficient
            (f"{ch_name}_parity_LSB", parity & 1),
        ]:
            bits = np.asarray(bits_data, dtype=np.uint8).flatten()
            data = bits_to_bytes_msb(bits)
            f = search_stream(f"{variant_name}", page_id, data)
            result["streams"].append(f)
    
    return result

UNSOVED_PAGES = [17, 20, 23, 25, 32, 40, 44, 50, 56, 57, 71]
SOLVED_BASELINES = [0, 3, 8]

print(f"Analyzing DCT coefficients of {len(UNSOVED_PAGES)} unsolved + {len(SOLVED_BASELINES)} baseline pages")
all_results = {}
hits = []

for page in UNSOVED_PAGES + SOLVED_BASELINES:
    page_id = f"{page:02d}"
    t0 = time.time()
    r = analyze_dct(page_id)
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
    yshape = r.get('y_shape', [])
    print(f"  {page_id}.jpg Y blocks={yshape[:2] if yshape else '?'}: {len(r['streams'])} streams in {dt:.1f}s, {meaningful} meaningful")

print(f"\n=== TOTAL MEANINGFUL DCT HITS: {len(hits)} ===")
for h in hits[:30]:
    s = h["findings"]
    print(f"  page={h['page']} stream={h['stream']}: magic={s['magic_matches']} pgp={s['pgp_matches']} urls={len(s['urls'])} hashes={len(s['hashes'])} ascii={len(s['ascii_strings'])} page56match={s['matches_page56']}")

with open(os.path.join(OUT_DIR, "dct_results.json"), "w") as f:
    json.dump({"all_results": all_results, "hits": hits}, f, indent=2, default=str)
print(f"\nResults saved to {OUT_DIR}/dct_results.json")
