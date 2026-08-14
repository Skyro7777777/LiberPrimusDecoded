#!/usr/bin/env python3
"""
simulated_annealing.py — SA + Latin quadgrams + keyword-derived alphabets
==========================================================================
Three parallel attacks to break the swap-only hill-climber local minimum:

Attack 1: Simulated Annealing with LARGER neighborhood moves
    - Moves: swap, segment-reverse (3-7), segment-rotate, single-element move
    - Schedule: T_start=2.0 -> T_end=0.01 over 50,000 iterations, geometric
    - Accept worse with prob exp(dS/T)
    - 50 restarts on page 50.jpg (91 runes) with identity=TH (best score -1057)

Attack 2: Latin quadgrams
    - Build Latin quadgram model from embedded Latin corpus (Cicero/Caesar/Vulgate)
    - Map Latin -> runes (lossy; classical Latin has 23 letters)
    - Re-score best SA candidate under Latin model
    - If Latin score >> Runeglish score => plaintext is Latin

Attack 3: Keyword-derived alphabets (direct construction)
    - Build keyed alphabet from Cicada-themed keywords
    - Check where F (decimal 0) lands = identity position
    - If matches NG(21)/W(7)/TH(2) -> candidate
    - Test as Quagmire III key on page 50.jpg with all 29 primers
"""
from __future__ import annotations
import sys, os, json, math, random, argparse, time
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, LETTERS, DECIMALS,
    N_RUNES, MOD, runes_to_decimals, decimals_to_runes, decimals_to_latin,
    runes_to_latin,
)
from first_diff_masc import (
    quadgram_score as runeglish_quadgram_score,
    first_differences, apply_masc, load_ngrams,
    QUADGRAMS as RUNEGLISH_QUAD, LOG_QUAD as RUNEGLISH_LOG, FLOOR_QUAD as RUNEGLISH_FLOOR,
)

DEC_DIR = os.path.dirname(os.path.abspath(__file__))
NGRAMS_DIR = os.path.join(DEC_DIR, "..", "solvers", "aldegonde", "src", "aldegonde", "data", "ngrams")

# ============================================================================
# LATIN N-GRAMS
# ============================================================================
# Latin -> rune mapping. Classical Latin has 23 letters (no J, U, W distinct from I, V).
# We map J->I, U->V, W->V (or W rune if we want to preserve); K, Q, Z -> drop or use closest.
LATIN_TO_RUNE_DEC = {
    'A': 24, 'B': 17, 'C': 5,  'D': 23, 'E': 18, 'F': 0,  'G': 6,  'H': 8,
    'I': 10, 'J': 10, 'K': 5,  'L': 20, 'M': 19, 'N': 9,  'O': 3,  'P': 13,
    'Q': 5,  'R': 4,  'S': 15, 'T': 16, 'U': 1,  'V': 1,  'W': 7,  'X': 14,
    'Y': 26, 'Z': 15,
}

# Embedded Latin corpus (mix of Cicero, Caesar, Vulgate, Seneca)
# Used to compute Latin quadgram log-probabilities in rune space.
LATIN_CORPUS = """
Gallia est omnis divisa in partes tres quarum unam incolunt Belgae aliam Aquitani
tertiam qui ipsorum lingua Celtae nostra Galli appellantur Hi omnes lingua institutis
rebus inter se differunt Gallos ab Aquitanis Garumna flumen dividit a Belgis Matrona et
Sequana dividunt Horum omnium fortissimi sunt Belgae propterea quod a cultu atque
humanitate provinciae longissime absunt minimeque ad eos mercatores saepe commeant
atque ea quae ad effeminandos animos pertinent important proximique sunt Germanis qui
trans Rhenum incolunt quibuscum continenter bellum gerunt Qua de causa Helvetii quoque
reliquae Gallos virtute praecedunt quod fere cotidianis proeliis cum Germanis
contendunt cum aut suis finibus eos prohibent aut ipsi in eorum finibus bellum gerunt

Qua de causa Caesar et Labienus consulibus uno ex minoribus consulibus Arvernorum
discessit ad suas legiones quas in Aquileiam hiemandi causa in finibus Carnorum
constituerat Eo cum venisset cognoscit ab exploratoribus et ab Celtis qui Ultra Rhenum incolunt
Sed de his rebus satis dictum est in prioribus commentariis Caesaris

Seneca Lucilio suo salutem Ita fac mi Lucili vindica te tibi et tempus quod adhuc aut
ereptum aut subductum aut iam fluxit collige servo Primum tempus quod ne quid
ocupatione tuae perderetnus servandum est et quod tutorii pueritiae fuit aut
contumacia progressus aut inanis ambitio aut lenta oblivio

Quod bonum felix faustum fortunatumque sit populo Romano Quiritium reique publicae
populi Romani Quiritium mihique et domo familiaeque nostrae salute reique publicae
populi Romani Quiritium saluti uti semper in omnibus rebus bene rem publicam
populi Romani Quiritium conservetis salvam sospitam incolumemque esse velitis
duelli permissum pro populo Romano Quiritium populo Romano Quiritium

Vita brevis ars longa occasiono fugace judicium difficile experimentum periculosum
Aequam memento rebus in arduis servare mentem In quiete et in Silva et in umbra
Vires acquirit eundo Ira furor brevis est an renum pertinax furor

Amicus verus est rara avis certa custodia vitae et pacis animae atque corporis
In quiete virtus et in labore sapientia Nihil est ab omni parte beatum
Nil admirari prope res est una Numici solaque quae possit facere et servare beatum

Omnibus modis hoc unum teneamus ut pareamus dis immortalibus et sequamur deorum
voluntatem Id est summum bonum sapientis nec sine deo nec contra deum fas est
Vera perfectaque sapientia Deos colere et parentes honorare et patriae prodesse
et amicos adiuvare et hostes cavere et inopem iuvare et innocentes defendere

Timeo danaos et dona ferentes Audentes fortuna iuvat Errare humanum est
Carpe diem quam minimum credula postero Memento mori Alea iacta est
Veni vidi vici Veni vidi vici Veni vidi vici Roma caput mundi
Si vis pacem para bellum Si vis pacem para bellum
Divide et impera Divide et impera Divide et impera
Ave Caesar morituri te salutant Ave Caesar morituri te salutant
Libertas id est veritas Veritas vos liberabit
Liber Primus Liber Primus Liber Primus
Intus si integer es omnia tuta foris Intus si integer es omnia tuta foris
Sic transit gloria mundi Sic transit gloria mundi
Per aspera ad astra Per aspera ad astra Per aspera ad astra
Ad astra per aspera Ad astra per aspera Ad astra per aspera
In omnibus rebus temet nosce In omnibus rebus temet nosce
Nosce te ipsum Nosce te ipsum Nosce te ipsum Nosce te ipsum

Vae victis Vae victis Vae victis Vae victis Vae victis
Memento mori Memento mori Memento mori Memento mori
Sub rosa Sub rosa Sub rosa
Deo volente Deo volente Deo volente Deo volente
Deus vult Deus vult Deus vult Deus vult
Ad maiorem Dei gloriam Ad maiorem Dei gloriam
Soli Deo gloria Soli Deo gloria Soli Deo gloria

Liber AL vel Legis sub figura CCXX as delivered by LXX L being the Angeli
of the Holy Books of Thelema Thelema Thelema Thelema
Do what thou wilt shall be the whole of the Law
Love is the law love under will
Every man and every woman is a star
For pure will unassuaged of purpose delivered from the lust of result
is in every way perfect

Habent sua fata libelli Habent sua fata libelli
In libris libertas In libris libertas
Bibliotheca omnium rerum Bibliotheca omnium rerum

Principibus placuisse viris non ultima laus est
Principibus placuisse viris non ultima laus est
O fortunatos nimium sua si bona norint agricolas
O fortunatos nimium sua si bona norint agricolas

Gloria in excelsis Deo et in terra pax hominibus bonae voluntatis
Gloria in excelsis Deo et in terra pax hominibus bonae voluntatis
Sanctus sanctus sanctus Dominus Deus Sabaoth
Pleni sunt caeli et terra gloria tua

Pater noster qui es in caelis sanctificetur nomen tuum adveniat regnum tuum
fiat voluntas tua sicut in caelo et in terra Panem nostrum supersubstantialem
da nobis hodie et dimitte nobis debita nostra sicut et nos dimittimus debitoribus
nostris et ne nos inducas in tentationem sed libera nos a malo amen
"""


def latin_text_to_runes(text: str) -> str:
    """Transliterate Latin text to runes (lossy). Drops chars not in LATIN_TO_RUNE_DEC."""
    decs = []
    for ch in text.upper():
        if ch in LATIN_TO_RUNE_DEC:
            decs.append(LATIN_TO_RUNE_DEC[ch])
    return decimals_to_runes(decs)


def build_latin_quadgrams():
    """Compute Latin quadgram log-probabilities in rune space."""
    rune_text = latin_text_to_runes(LATIN_CORPUS)
    counts = Counter()
    for i in range(len(rune_text) - 3):
        counts[rune_text[i:i+4]] += 1
    total = sum(counts.values()) or 1
    log_probs = {k: math.log(v / total) for k, v in counts.items()}
    floor = math.log(0.01 / total)
    return log_probs, floor, len(counts), len(rune_text)


LATIN_LOG_QUAD, LATIN_FLOOR, N_LATIN_QUAD, LATIN_CORPUS_LEN = build_latin_quadgrams()


def latin_quadgram_score(rune_str: str) -> float:
    """Score a rune string using Latin quadgram log-probabilities."""
    if len(rune_str) < 4:
        return LATIN_FLOOR * max(1, len(rune_str))
    s = 0.0
    for i in range(len(rune_str) - 3):
        s += LATIN_LOG_QUAD.get(rune_str[i:i+4], LATIN_FLOOR)
    return s


# ============================================================================
# SIMULATED ANNEALING
# ============================================================================
def mutate_swap(perm):
    i, j = random.sample(range(N_RUNES), 2)
    perm[i], perm[j] = perm[j], perm[i]
    return ('swap', i, j)


def mutate_reverse(perm):
    n = N_RUNES
    seg_len = random.randint(3, 7)
    start = random.randint(0, n - seg_len)
    end = start + seg_len
    perm[start:end] = perm[start:end][::-1]
    return ('reverse', start, end)


def mutate_rotate(perm):
    n = N_RUNES
    seg_len = random.randint(3, 7)
    start = random.randint(0, n - seg_len)
    end = start + seg_len
    seg = perm[start:end]
    k = random.randint(1, seg_len - 1)
    perm[start:end] = seg[k:] + seg[:k]
    return ('rotate', start, end, k)


def mutate_move(perm):
    n = N_RUNES
    i = random.randint(0, n - 1)
    j = random.randint(0, n - 1)
    while j == i:
        j = random.randint(0, n - 1)
    el = perm.pop(i)
    perm.insert(j, el)
    return ('move', i, j)


def undo_mutate(perm, mut):
    """Reverse a mutation in-place."""
    kind = mut[0]
    if kind == 'swap':
        _, i, j = mut
        perm[i], perm[j] = perm[j], perm[i]
    elif kind == 'reverse':
        _, start, end = mut
        perm[start:end] = perm[start:end][::-1]
    elif kind == 'rotate':
        _, start, end, k = mut
        seg = perm[start:end]
        # forward was seg[k:] + seg[:k]; reverse: seg[-k:] + seg[:-k]
        seg_len = end - start
        k_back = (seg_len - k) % seg_len
        if k_back == 0:
            return
        perm[start:end] = seg[k_back:] + seg[:k_back]
    elif kind == 'move':
        _, i, j = mut
        # element was moved from i to j; to undo, move from j back to i
        el = perm.pop(j)
        perm.insert(i, el)


MUTATORS = [mutate_swap, mutate_reverse, mutate_rotate, mutate_move]


def decrypt_with_perm(ct_decs, primer_dec, perm):
    """First-difference autokey + MASC decryption."""
    diffs = first_differences(ct_decs, primer_dec)
    pt_decs = apply_masc(diffs, perm)
    return decimals_to_runes(pt_decs)


def score_perm(ct_decs, primer_dec, perm, score_fn=None):
    """Score a (perm, primer) candidate."""
    if score_fn is None:
        score_fn = runeglish_quadgram_score
    pt_runes = decrypt_with_perm(ct_decs, primer_dec, perm)
    return score_fn(pt_runes), pt_runes


def find_best_primer_for_perm(ct_decs, perm, score_fn=None, verbose=False):
    """Try all 29 primers, return (best_primer, best_score, best_pt_runes)."""
    if score_fn is None:
        score_fn = runeglish_quadgram_score
    best_primer = 0
    best_score = -1e18
    best_pt = None
    for primer in range(N_RUNES):
        pt_runes = decrypt_with_perm(ct_decs, primer, perm)
        s = score_fn(pt_runes)
        if s > best_score:
            best_score = s
            best_primer = primer
            best_pt = pt_runes
    return best_primer, best_score, best_pt


def make_perm_with_identity_at_0(identity_dec):
    """Random permutation but with perm[0] = identity_dec (rune that diff=0 maps to)."""
    others = [d for d in range(N_RUNES) if d != identity_dec]
    random.shuffle(others)
    perm = [identity_dec] + others
    return perm


def simulated_annealing(ct_decs, identity_dec, max_iter=50000, T_start=2.0, T_end=0.01,
                         restart_idx=0, verbose=False, score_fn=None):
    """
    Run one SA restart. Returns (best_perm, best_primer, best_score, best_pt_runes).
    """
    if score_fn is None:
        score_fn = runeglish_quadgram_score
    # Initialize: random perm with identity at position 0
    perm = make_perm_with_identity_at_0(identity_dec)
    # Find best primer for this initial perm
    primer, cur_score, cur_pt = find_best_primer_for_perm(ct_decs, perm, score_fn)
    best_perm = perm[:]
    best_primer = primer
    best_score = cur_score
    best_pt = cur_pt

    log_ratio = math.log(T_end / T_start) if T_start > 0 and T_end > 0 else 0
    last_print = time.time()
    for it in range(max_iter):
        T = T_start * math.exp(log_ratio * (it / max_iter)) if T_start > 0 else T_end
        # Mutate
        mutator = random.choice(MUTATORS)
        mut = mutator(perm)
        # Try keeping same primer (fast) OR re-evaluate primer occasionally
        if random.random() < 0.05:
            new_primer, new_score, new_pt = find_best_primer_for_perm(ct_decs, perm, score_fn)
        else:
            new_primer = primer
            new_pt = decrypt_with_perm(ct_decs, primer, perm)
            new_score = score_fn(new_pt)
        delta = new_score - cur_score
        if delta > 0 or (T > 0 and random.random() < math.exp(delta / T)):
            # Accept
            cur_score = new_score
            primer = new_primer
            cur_pt = new_pt
            if new_score > best_score:
                best_score = new_score
                best_perm = perm[:]
                best_primer = primer
                best_pt = new_pt
                if verbose and (time.time() - last_print > 5 or new_score > best_score - 5):
                    print(f"  [r{restart_idx} it{it:5d} T={T:.3f}] score={new_score:8.1f}  {runes_to_latin(new_pt)[:80]}")
                    last_print = time.time()
        else:
            # Reject — undo mutation
            undo_mutate(perm, mut)
    return best_perm, best_primer, best_score, best_pt


def run_sa_attack(ct_runes, identity_dec, restarts=50, max_iter=50000, verbose=True, score_fn=None):
    """Run multiple SA restarts, return overall best."""
    if score_fn is None:
        score_fn = runeglish_quadgram_score
    ct_decs = runes_to_decimals(ct_runes)
    overall_best = None
    t0 = time.time()
    for r in range(restarts):
        perm, primer, score, pt = simulated_annealing(
            ct_decs, identity_dec, max_iter=max_iter, restart_idx=r,
            verbose=(verbose and r == 0), score_fn=score_fn,
        )
        if overall_best is None or score > overall_best[2]:
            overall_best = (perm, primer, score, pt)
            print(f"  [restart {r}] NEW BEST score={score:.1f}  primer={DEC_TO_LETTER[primer]}  {runes_to_latin(pt)[:80]}")
        if verbose and r % 5 == 0:
            elapsed = time.time() - t0
            print(f"  [restart {r}/{restarts}] elapsed={elapsed:.1f}s  best={overall_best[2]:.1f}")
    return overall_best


# ============================================================================
# ATTACK 3: KEYWORD-DERIVED ALPHABETS
# ============================================================================
# Letter -> rune decimal mapping (using full LETTERS list)
LETTER_TO_DEC = {l: i for i, l in enumerate(LETTERS)}


def keyword_to_keyed_alphabet(keyword: str):
    """
    Build a keyed alphabet (perm) from a keyword.
    Returns perm (list of 29 rune decimals) where perm[i] = rune at position i.
    Keyword letters are deduplicated; remaining runes appended in standard order.
    """
    seen = set()
    keyword_decs = []
    for ch in keyword.upper():
        if ch in LETTER_TO_DEC and ch not in seen:
            keyword_decs.append(LETTER_TO_DEC[ch])
            seen.add(ch)
    remaining = [d for d in range(N_RUNES) if d not in seen]
    return keyword_decs + remaining


def find_f_position(perm):
    """Return the position of F (decimal 0) in the perm."""
    return perm.index(0)


def run_keyword_attack(ct_runes, score_fn=None):
    """Test all Cicada-themed keywords. Returns list of dicts."""
    if score_fn is None:
        score_fn = runeglish_quadgram_score
    ct_decs = runes_to_decimals(ct_runes)
    keywords = [
        "PRIMESARESACRED", "INSTAR", "LIBER", "PRIMUS", "INTUS", "SACRED",
        "WELCOME", "PARABLE", "EMERGENCE", "DIVINITY", "CIRCUMFERENCE",
        "FIRFUMFERENFE", "PRIMES", "SACREDPRIMES", "LIBERPRIMUS",
        "LIBERPRIMI", "ANINSTRVCTIAN", "THELEMA", "CAESAR", "CICERO",
        "VERITAS", "VOLVNTAS", "DOITTHOVWILT", "LOVE", "AEONS",
        "THELEMITES", "TEITAN", "VOS", "PARSIFAL", "IAO",
    ]
    target_identity_decs = {21: "NG", 7: "W", 2: "TH"}
    results = []
    for kw in keywords:
        perm = keyword_to_keyed_alphabet(kw)
        f_pos = find_f_position(perm)
        perm0_letter = DEC_TO_LETTER[perm[0]]
        matches_target = f_pos in target_identity_decs
        # Test as direct key: try all 29 primers, find best
        best_primer, best_score, best_pt = find_best_primer_for_perm(ct_decs, perm, score_fn)
        results.append({
            "keyword": kw,
            "perm": perm,
            "perm_letters": [DEC_TO_LETTER[d] for d in perm],
            "perm_0": perm[0],
            "perm_0_letter": perm0_letter,
            "f_position": f_pos,
            "f_position_letter": DEC_TO_LETTER[f_pos],
            "matches_identity_target": matches_target,
            "target_match": target_identity_decs.get(f_pos, None),
            "best_primer": best_primer,
            "best_primer_letter": DEC_TO_LETTER[best_primer],
            "best_score": best_score,
            "best_pt_latin": runes_to_latin(best_pt),
            "best_pt_runes": best_pt,
        })
    return results


# ============================================================================
# ATTACK 2: LATIN QUADGRAM RE-SCORING
# ============================================================================
def rescore_with_latin(ct_runes, perm, primer):
    """Decrypt with given (perm, primer), then score under Latin model."""
    ct_decs = runes_to_decimals(ct_runes)
    pt_runes = decrypt_with_perm(ct_decs, primer, perm)
    rg_score = runeglish_quadgram_score(pt_runes)
    lat_score = latin_quadgram_score(pt_runes)
    return pt_runes, rg_score, lat_score


def run_latin_hillclimb(ct_runes, identity_dec, restarts=10, max_iter=10000):
    """Hill-climb using Latin quadgram score instead of Runeglish."""
    return run_sa_attack(ct_runes, identity_dec, restarts=restarts, max_iter=max_iter,
                         verbose=False, score_fn=latin_quadgram_score)


# ============================================================================
# MAIN
# ============================================================================
def load_unsolved():
    with open(os.path.join(DEC_DIR, "unsolved_pages.json")) as f:
        return json.load(f)


def find_page(pages, page_id, header_substr=None):
    """Find a page by page_id (and optionally header substring)."""
    candidates = [p for p in pages if p["page_id"] == page_id]
    if header_substr:
        candidates = [p for p in candidates if header_substr in p.get("header", "")]
    return candidates[0] if candidates else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="50.jpg")
    ap.add_argument("--identity", default="TH", choices=["TH", "NG", "W", "F"])
    ap.add_argument("--restarts", type=int, default=50)
    ap.add_argument("--iterations", type=int, default=50000)
    ap.add_argument("--attacks", default="all", help="Comma-separated: sa,latin,keyword,all")
    args = ap.parse_args()

    pages = load_unsolved()
    # The 91-rune page 50.jpg is the SHORT one (first occurrence with that page_id).
    # We want the one with n_runes ~ 91.
    page_candidates = [p for p in pages if p["page_id"] == args.page]
    if not page_candidates:
        print(f"Page {args.page} not found!")
        return
    # Pick the smallest (short page)
    page = min(page_candidates, key=lambda p: p["n_runes"])
    print(f"Target page: {page['page_id']} ({page['n_runes']} runes)")
    print(f"Header: {page['header']}")
    print(f"Runes (first 80): {page['runes'][:80]}")

    ct_runes = page["runes"]
    ct_decs = runes_to_decimals(ct_runes)

    identity_letter = args.identity
    identity_dec = LETTERS.index(identity_letter)
    print(f"Identity (perm[0]) = {identity_letter} (dec={identity_dec})")
    print(f"Latin quadgrams loaded: {N_LATIN_QUAD} unique (from {LATIN_CORPUS_LEN} rune-chars)")
    print(f"Runeglish quadgrams: {len(RUNEGLISH_QUAD)} unique")
    print()

    attacks = set(args.attacks.split(","))
    run_all = "all" in attacks
    results = {"page": args.page, "n_runes": page["n_runes"], "identity": identity_letter,
               "n_latin_quadgrams": N_LATIN_QUAD, "n_runeglish_quadgrams": len(RUNEGLISH_QUAD)}

    # Baseline: identity permutation (no MASC) for comparison
    print("=" * 70)
    print("BASELINE: identity perm (no MASC), all 29 primers")
    print("=" * 70)
    id_perm = list(range(N_RUNES))
    bp, bs, bpt = find_best_primer_for_perm(ct_decs, id_perm)
    print(f"  Best primer={DEC_TO_LETTER[bp]}  score={bs:.1f}  pt={runes_to_latin(bpt)[:80]}")
    results["baseline"] = {"primer": DEC_TO_LETTER[bp], "score": bs,
                            "pt": runes_to_latin(bpt)}

    # ---------------- ATTACK 1: SA ----------------
    if run_all or "sa" in attacks:
        print()
        print("=" * 70)
        print(f"ATTACK 1: SIMULATED ANNEALING (restarts={args.restarts}, iter={args.iterations})")
        print("=" * 70)
        sa_best = run_sa_attack(ct_runes, identity_dec,
                                 restarts=args.restarts, max_iter=args.iterations,
                                 verbose=True)
        perm, primer, score, pt = sa_best
        print()
        print(f">>> SA BEST: score={score:.1f}  primer={DEC_TO_LETTER[primer]}  perm[0]={DEC_TO_LETTER[perm[0]]}")
        print(f"    Plaintext (Latin): {runes_to_latin(pt)}")
        print(f"    Plaintext (Runes): {pt}")
        print(f"    Permutation: {[DEC_TO_LETTER[d] for d in perm]}")
        results["sa_best"] = {
            "score": score, "primer": DEC_TO_LETTER[primer],
            "perm": [DEC_TO_LETTER[d] for d in perm],
            "perm_0": DEC_TO_LETTER[perm[0]],
            "pt_latin": runes_to_latin(pt),
            "pt_runes": pt,
            "improvement_over_baseline": score - bs,
        }

    # ---------------- ATTACK 2: LATIN ----------------
    if run_all or "latin" in attacks:
        print()
        print("=" * 70)
        print("ATTACK 2: LATIN QUADGRAMS HILL-CLIMB")
        print("=" * 70)
        # First: re-score the SA best (if available) with Latin model
        if "sa_best" in results:
            sa_perm_letters = results["sa_best"]["perm"]
            sa_perm = [LETTERS.index(l) for l in sa_perm_letters]
            sa_primer = LETTERS.index(results["sa_best"]["primer"])
            pt_runes, rg_s, lat_s = rescore_with_latin(ct_runes, sa_perm, sa_primer)
            print(f"  SA best re-scored: Runeglish={rg_s:.1f}  Latin={lat_s:.1f}")
            print(f"    Plaintext: {runes_to_latin(pt_runes)[:80]}")
            results["sa_rescored_latin"] = {"runeglish": rg_s, "latin": lat_s,
                                             "pt": runes_to_latin(pt_runes)}
        # Now: run a small Latin-only hill-climb
        print(f"\n  Running Latin-only SA (10 restarts, 10000 iter)...")
        lat_best = run_latin_hillclimb(ct_runes, identity_dec, restarts=10, max_iter=10000)
        lperm, lprimer, lscore, lpt = lat_best
        # Compare Latin vs Runeglish on the Latin-optimal plaintext
        rg_on_lat_pt = runeglish_quadgram_score(lpt)
        print(f"\n>>> LATIN HILL-CLIMB BEST: Latin score={lscore:.1f}  Runeglish on same PT={rg_on_lat_pt:.1f}")
        print(f"    Primer={DEC_TO_LETTER[lprimer]}  perm[0]={DEC_TO_LETTER[lperm[0]]}")
        print(f"    Plaintext: {runes_to_latin(lpt)}")
        results["latin_hillclimb_best"] = {
            "latin_score": lscore, "runeglish_on_same_pt": rg_on_lat_pt,
            "primer": DEC_TO_LETTER[lprimer],
            "perm_0": DEC_TO_LETTER[lperm[0]],
            "pt": runes_to_latin(lpt),
            "is_latin": (lscore > rg_on_lat_pt + 50),
        }

    # ---------------- ATTACK 3: KEYWORD ----------------
    if run_all or "keyword" in attacks:
        print()
        print("=" * 70)
        print("ATTACK 3: KEYWORD-DERIVED ALPHABETS")
        print("=" * 70)
        kw_results = run_keyword_attack(ct_runes)
        # Sort by score
        kw_results.sort(key=lambda r: -r["best_score"])
        print(f"\nTop 10 keyword candidates by Runeglish score:")
        for r in kw_results[:10]:
            print(f"  {r['keyword']:20s}  perm[0]={r['perm_0_letter']:3s}  F@{r['f_position']:2d}({r['f_position_letter']:3s})"
                  f"  {'MATCH' if r['matches_identity_target'] else '      '}  score={r['best_score']:8.1f}"
                  f"  pt={r['best_pt_latin'][:60]}")
        print(f"\nKeywords with F-position matching NG(21)/W(7)/TH(2):")
        matched = [r for r in kw_results if r["matches_identity_target"]]
        if matched:
            for r in matched:
                print(f"  {r['keyword']:20s}  F@{r['f_position']:2d}({r['target_match']})"
                      f"  score={r['best_score']:8.1f}  pt={r['best_pt_latin'][:80]}")
        else:
            print("  (none)")
        results["keyword_attack"] = {
            "n_tested": len(kw_results),
            "top5_by_score": [{"keyword": r["keyword"], "perm_0": r["perm_0_letter"],
                                "f_position": r["f_position"], "f_pos_letter": r["f_position_letter"],
                                "score": r["best_score"], "pt": r["best_pt_latin"][:120]} for r in kw_results[:5]],
            "matched_identity_target": [{"keyword": r["keyword"], "f_position": r["f_position"],
                                          "target": r["target_match"], "score": r["best_score"],
                                          "pt": r["best_pt_latin"][:120]} for r in matched],
        }

    # Save results
    out_path = os.path.join(DEC_DIR, "simulated_annealing_results.json")
    with open(out_path, "w") as f:
        # Strip non-serializable
        safe = {}
        for k, v in results.items():
            if isinstance(v, dict):
                safe[k] = {kk: vv for kk, vv in v.items()
                            if not isinstance(vv, (list,)) or all(not isinstance(x, dict) or True for x in vv)}
            else:
                safe[k] = v
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {out_path}")
    return results


if __name__ == "__main__":
    main()
