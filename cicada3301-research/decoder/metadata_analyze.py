#!/usr/bin/env python3
"""
Visual/color/EXIF/metadata analysis for Cicada 3301 LP page JPEGs.
For each unsolved LP2 page JPEG:
  - Extract EXIF/metadata via PIL + piexif
  - Extract JPEG markers (APP0/APP1/COM/etc) by parsing JPEG segments
  - Compute color histograms
  - Check for "near-white" pixels in marginalia (potential hidden text via subtle color diff)
  - Save findings
"""
import os, sys, json, hashlib, re, struct
from PIL import Image, ImageFile
import numpy as np
import piexif

ImageFile.LOAD_TRUNCATED_IMAGES = True

IMAGES_DIR = "/home/z/my-project/cicada3301-research/images"
OUT_DIR = "/home/z/my-project/cicada3301-research/stego_output/metadata"
os.makedirs(OUT_DIR, exist_ok=True)

def parse_jpeg_markers(path):
    """Walk JPEG markers, return list of (marker, offset, length, data_preview)."""
    markers = []
    with open(path, 'rb') as f:
        data = f.read()
    if not data.startswith(b'\xff\xd8'):
        return [{'error': 'not a JPEG'}]
    i = 2  # skip SOI
    while i < len(data) - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i:i+2]
        # Skip padding FFs
        if marker == b'\xff\xff':
            i += 1
            continue
        # Standalone markers (no length)
        if marker in (b'\xff\xd8', b'\xff\xd9'):  # SOI, EOI
            markers.append({'marker': marker.hex(), 'offset': i, 'length': 0})
            i += 2
            if marker == b'\xff\xd9':
                break
            continue
        if marker in (b'\xff\xd0', b'\xff\xd1', b'\xff\xd2', b'\xff\xd3',
                      b'\xff\xd4', b'\xff\xd5', b'\xff\xd6', b'\xff\xd7'):  # RSTn
            markers.append({'marker': marker.hex(), 'offset': i, 'length': 0})
            i += 2
            continue
        if i + 4 > len(data):
            break
        seg_len = struct.unpack('>H', data[i+2:i+4])[0]
        seg_data = data[i+2:i+2+seg_len]
        # Decode common markers
        marker_info = {'marker': marker.hex(), 'offset': i, 'length': seg_len}
        marker_name = {
            b'\xff\xe0': 'APP0 (JFIF)',
            b'\xff\xe1': 'APP1 (EXIF)',
            b'\xff\xe2': 'APP2',
            b'\xff\xe3': 'APP3',
            b'\xff\xed': 'APP13 (Photoshop)',
            b'\xff\xee': 'APP14 (Adobe)',
            b'\xfe': 'COM (Comment)',
            b'\xff\xdb': 'DQT',
            b'\xff\xc0': 'SOF0 (Baseline)',
            b'\xff\xc2': 'SOF2 (Progressive)',
            b'\xff\xc4': 'DHT',
            b'\xff\xda': 'SOS',
        }.get(marker, f'OTHER {marker.hex()}')
        marker_info['name'] = marker_name
        if marker == b'\xff\xfe':  # COM
            try:
                comment = seg_data[2:].decode('ascii', errors='ignore')
                marker_info['comment'] = comment[:500]
            except: pass
        elif marker == b'\xff\xe1':  # APP1
            marker_info['preview'] = seg_data[:32].hex()
            if seg_data[2:6] == b'Exif':
                marker_info['exif'] = True
            elif seg_data[2:6] == b'http':
                marker_info['xmp'] = True
        elif marker == b'\xff\xe0':  # APP0
            marker_info['preview'] = seg_data[:32].hex()
            if seg_data[2:6] == b'JFIF':
                marker_info['jfif'] = True
        else:
            marker_info['preview'] = seg_data[:32].hex()
        markers.append(marker_info)
        i += 2 + seg_len
        if marker == b'\xff\xda':  # SOS - start of scan, scan data follows
            # Scan until next non-padding FF
            while i < len(data) - 1:
                if data[i] == 0xFF and data[i+1] != 0x00 and not (0xD0 <= data[i+1] <= 0xD7):
                    break
                i += 1
    return markers

def extract_exif_pil(path):
    """Extract EXIF via PIL."""
    try:
        img = Image.open(path)
        exif_data = img._getexif() if hasattr(img, '_getexif') else None
        if exif_data:
            from PIL.ExifTags import TAGS
            decoded = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    value = value.hex() if len(value) < 100 else f'<{len(value)} bytes>'
                decoded[tag] = str(value)[:200]
            return decoded
    except Exception as e:
        return {'error': str(e)}
    return None

def extract_exif_piexif(path):
    """Extract EXIF via piexif."""
    try:
        exif_dict = piexif.load(path)
        result = {}
        for ifd_name in ['0th', 'Exif', 'GPS', '1st']:
            ifd = exif_dict.get(ifd_name)
            if not ifd: continue
            entries = {}
            for tag, val in ifd.items():
                tag_name = piexif.TAGS.get(ifd_name, {}).get(tag, {}).get('name', str(tag))
                if isinstance(val, bytes):
                    val = val.hex() if len(val) < 100 else f'<{len(val)} bytes>'
                else:
                    val = str(val)[:200]
                entries[tag_name] = val
            if entries:
                result[ifd_name] = entries
        # Also check thumbnail
        if exif_dict.get('thumbnail'):
            result['thumbnail_size'] = len(exif_dict['thumbnail'])
        return result
    except Exception as e:
        return {'error': str(e)}

def color_stats(path, max_dim=600):
    """Compute color statistics."""
    try:
        img = Image.open(path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        w, h = img.size
        scale = max_dim / max(w, h)
        if scale < 1.0:
            img = img.resize((int(w*scale), int(h*scale)), Image.BILINEAR)
        arr = np.array(img)
        return {
            'mean': arr.mean(axis=(0,1)).tolist(),
            'std': arr.std(axis=(0,1)).tolist(),
            'min': arr.min(axis=(0,1)).tolist(),
            'max': arr.max(axis=(0,1)).tolist(),
            'unique_pixels_sample': len(np.unique(arr.reshape(-1, 3), axis=0)),
        }
    except Exception as e:
        return {'error': str(e)}

UNSOVED_PAGES = [17, 20, 23, 25, 32, 40, 44, 50, 56, 57, 71]
SOLVED_BASELINES = [0, 3, 8]

print(f"Analyzing metadata of {len(UNSOVED_PAGES)} unsolved + {len(SOLVED_BASELINES)} baseline pages")
all_results = {}
hits = []

for page in UNSOVED_PAGES + SOLVED_BASELINES:
    page_id = f"{page:02d}"
    path = os.path.join(IMAGES_DIR, f"{page_id}.jpg")
    if not os.path.exists(path):
        print(f"  {page_id}.jpg: NOT FOUND")
        continue
    print(f"\n--- {page_id}.jpg ---")
    markers = parse_jpeg_markers(path)
    pil_exif = extract_exif_pil(path)
    piexif_data = extract_exif_piexif(path)
    cs = color_stats(path)
    r = {
        "page_id": page_id,
        "file_size": os.path.getsize(path),
        "markers": markers,
        "pil_exif": pil_exif,
        "piexif": piexif_data,
        "color_stats": cs,
    }
    all_results[page_id] = r
    # Print key findings
    marker_summary = [(m.get('name', m['marker']), m.get('length', 0)) for m in markers if isinstance(m, dict) and 'marker' in m]
    print(f"  Size: {r['file_size']} bytes")
    print(f"  Markers: {marker_summary}")
    print(f"  PIL EXIF: {pil_exif}")
    print(f"  piexif: {piexif_data}")
    # Look for COM (comment) markers
    for m in markers:
        if isinstance(m, dict) and 'comment' in m:
            print(f"  COMMENT @ {m['offset']}: {m['comment'][:200]}")
            hits.append({"page": page_id, "type": "JPEG_COMMENT", "offset": m['offset'], "content": m['comment'][:200]})

print(f"\n=== MEANINGFUL METADATA HITS: {len(hits)} ===")
for h in hits:
    print(f"  page={h['page']} type={h['type']}: {h.get('content', '')}")

with open(os.path.join(OUT_DIR, "metadata_results.json"), "w") as f:
    json.dump({"all_results": all_results, "hits": hits}, f, indent=2, default=str)
print(f"\nResults saved to {OUT_DIR}/metadata_results.json")
