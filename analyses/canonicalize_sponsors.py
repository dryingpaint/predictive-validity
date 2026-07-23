"""Sponsor canonicalization v2 — thorough alias + pattern handling."""
import csv
import os
import re
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor


# Canonical name → list of substring aliases. Longest alias should win.
# Only match if alias is a WHOLE-WORD substring (not "syndax" matching "syndaxonline").
ALIAS_GROUPS = {
    # ===== Big Pharma (US) =====
    "Eli Lilly": ["eli lilly", "eli-lilly", "lilly usa", "lilly research", "loxo oncology", "prevail therapeutics"],
    "Pfizer": ["pfizer", "wyeth", "pharmacia", "seagen", "seattle genetics", "arena pharmaceuticals", "biohaven",
               "medivation", "hospira", "trillium therapeutics", "array biopharma"],
    "Bristol Myers Squibb": ["bristol-myers squibb", "bristol myers squibb", "bms", "celgene", "myokardia",
                              "mirati therapeutics", "juno therapeutics", "rigel bristol", "turning point therapeutics"],
    "AbbVie": ["abbvie", "allergan", "abbott laboratories", "abbott pharmaceuticals", "stemcentrx",
               "pharmacyclics", "immunogen", "cerevel"],
    "Merck (MSD)": ["merck sharp", "merck sharp & dohme", "msd ", "msd,", "msd(", "msd)",
                    "merck & co", "merck and co", "merck usa", "acceleron pharma", "peloton therapeutics",
                    "imago biosciences", "cubist pharmaceuticals", "arqule", "afferent pharmaceuticals",
                    "immune design", "harpoon therapeutics", "oncoimmune", "prometheus biosciences",
                    "verona pharma", "cidara therapeutics", "oncoethix", "eyebio"],
    "AstraZeneca": ["astrazeneca", "astra zeneca", "medimmune", "alexion", "syntimmune", "wilson therapeutics",
                    "achaogen", "gracell", "amolyt pharma", "acerta pharma"],
    "Johnson & Johnson (Janssen)": ["janssen", "actelion", "momenta pharmaceuticals",
                                     "abiomed", "xian janssen", "xenon johnson"],
    "GlaxoSmithKline (GSK)": ["glaxosmithkline", "gsk ", "gsk,", "gsk(", "gsk-",
                               "smithkline beecham", "glaxo smith kline", "sierra oncology", "affinivax",
                               "tesaro", "adaptimmune gsk", "human genome sciences", "bellus health",
                               "boston pharmaceuticals"],
    "Sanofi": ["sanofi", "sanofi-aventis", "sanofi aventis", "aventis", "genzyme", "sanofi pasteur",
               "kymab", "kadmon", "principia biopharma", "translate bio", "avexis"],
    "Bayer": ["bayer ", "bayer,", "bayer(", "bayer-", "bayer healthcare", "bayer schering", "bluerock", "vividion"],
    "Boehringer Ingelheim": ["boehringer ingelheim", "boehringer-ingelheim", "boehringer inge"],
    "Takeda": ["takeda", "shire", "millennium pharmaceuticals", "ariad", "nimble therapeutics"],
    "Amgen": ["amgen", "immunex", "onyx pharmaceuticals", "chemocentryx", "horizon therapeutics", "five prime therapeutics"],
    "Gilead": ["gilead", "kite pharma", "immunomedics", "forty seven"],
    "Novartis": ["novartis", "sandoz", "chinook therapeutics", "advanced accelerator applications",
                 "endocyte", "medicines company", "the medicines company", "gyroscope therapeutics", "vedere bio"],
    "Roche / Genentech": ["roche", "hoffmann-la roche", "hoffmann la roche", "genentech",
                            "chugai pharmaceutical", "spark therapeutics", "poseida therapeutics",
                            "flatiron", "recursion pharmaceuticals roche"],

    # ===== German Merck (KGaA) — separate =====
    "Merck KGaA": ["merck kgaa", "merck healthcare kgaa", "emd serono", "merck healthcare",
                    "springworks therapeutics"],

    # ===== Other big / mid pharma =====
    "Novo Nordisk": ["novo nordisk"],
    "Regeneron": ["regeneron"],
    "Vertex": ["vertex pharmaceuticals", "vertex "],
    "BioMarin": ["biomarin"],
    "Alnylam": ["alnylam"],
    "Ionis": ["ionis pharmaceuticals", "ionis ", "isis pharmaceuticals"],
    "Blueprint Medicines": ["blueprint medicines"],
    "BeiGene / BeOne": ["beigene", "beone"],
    "Syndax": ["syndax"],
    "G1 Therapeutics": ["g1 therapeutics"],
    "PTC Therapeutics": ["ptc therapeutics"],
    "Jazz Pharmaceuticals": ["jazz pharmaceuticals"],
    "Bausch Health / Valeant": ["bausch health", "valeant"],
    "Otsuka": ["otsuka"],
    "Sun Pharmaceutical": ["sun pharma"],
    "Bavarian Nordic": ["bavarian nordic"],
    "ImmunityBio": ["immunitybio", "nantkwest"],
    "Ipsen": ["ipsen"],
    "Servier": ["servier"],
    "Daiichi Sankyo": ["daiichi sankyo", "daiichi-sankyo"],
    "Astellas": ["astellas"],
    "Eisai": ["eisai"],
    "Chugai": ["chugai"],  # Note: partly Roche owned but reports separately
    "Ono Pharmaceutical": ["ono pharma"],
    "Sumitomo": ["sumitomo dainippon", "sumitomo pharma"],
    "Kyowa Kirin": ["kyowa kirin", "kyowa hakko"],
    "Mitsubishi Tanabe": ["mitsubishi tanabe"],
    "Shionogi": ["shionogi"],
    "Incyte": ["incyte"],
    "Moderna": ["moderna"],
    "BioNTech": ["biontech"],
    "UCB": ["ucb biopharma", "ucb biosciences", "ucb pharma", "ucb celltech", "ucb japan",
             "ucb, ", "ucb ("],
    "BridgeBio Pharma": ["bridgebio pharma", "bridgebio,", "bridgebio ", "bridgebio"],
    "Chiesi": ["chiesi"],
    "Grifols": ["grifols"],
    "CSL Behring": ["csl behring", "csl limited"],
    "Merus": ["merus"],
    "Genmab": ["genmab"],
    "Argenx": ["argenx"],
    "Ascendis Pharma": ["ascendis"],
    "Ultragenyx": ["ultragenyx"],
    "Sarepta": ["sarepta"],
    "Alkermes": ["alkermes"],
    "Neurocrine Biosciences": ["neurocrine"],
    "Intercept Pharmaceuticals": ["intercept pharmaceutical"],
    "Reata Pharmaceuticals": ["reata"],
    "Halozyme": ["halozyme"],
    "Deciphera": ["deciphera"],
    "MacroGenics": ["macrogenics"],
    "Fate Therapeutics": ["fate therapeutics"],
    "Iovance Biotherapeutics": ["iovance"],
    "Krystal Biotech": ["krystal biotech"],
    "TG Therapeutics": ["tg therapeutics"],
    "Coherus": ["coherus"],
    "Epizyme": ["epizyme"],
    "Puma Biotechnology": ["puma biotechnology"],
    "Lexicon": ["lexicon pharmaceuticals"],
    "Syros": ["syros"],
    "Portola Pharmaceuticals": ["portola"],
    "Ascentage Pharma": ["ascentage"],
    "HUTCHMED": ["hutchmed"],
    "PharmaMar": ["pharmamar"],
    "Hansoh Pharma": ["hansoh"],
    "Innovent": ["innovent"],
    "Junshi Biosciences": ["junshi"],
    "Sino Biopharm / Chia Tai Tianqing": ["sino biopharm", "chia tai tianqing"],
    "Jiangsu Hengrui": ["hengrui"],
    "Ascentage Pharma Group Inc.": ["ascentage pharma group"],
    "Bristol Bio": [],  # keep separate to avoid mix with BMS
}


def _tokenize(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())


def normalize_sponsor(raw: str) -> str:
    if not raw:
        return "Unknown"
    s = raw.strip()
    s_low = s.lower()

    # Extract corporate lineage from patterns:
    #   "X, a [wholly[-]owned] subsidiary of Y[, ...]"
    #   "X, an affiliate of Y[, ...]"
    #   "X, a Y company"
    #   "X, a healthcare company of Y"
    lineage_parent = None
    for pat in [
        r"subsidiary of\s+([^,()\.]+?)(?:[,()\.]|\s+inc\.|\s+llc|\s+ltd|\s+corp|$)",
        r"affiliate of\s+([^,()\.]+?)(?:[,()\.]|\s+inc\.|\s+llc|\s+ltd|\s+corp|$)",
        r"healthcare company of\s+([^,()\.]+?)(?:[,()\.]|\s+inc\.|\s+llc|\s+ltd|\s+corp|$)",
        r",\s*a\s+([a-zA-Z][a-zA-Z0-9 &\-]+?)\s+company\b",
    ]:
        m = re.search(pat, s_low)
        if m:
            lineage_parent = m.group(1).strip()
            break

    if lineage_parent:
        # Look up parent in aliases
        for canonical, aliases in ALIAS_GROUPS.items():
            for a in aliases:
                if a in lineage_parent:
                    return canonical
        # Otherwise use parent name directly (title-cased)
        return " ".join(w.capitalize() for w in lineage_parent.split())

    # Direct alias match — longest first
    all_aliases = [(canonical, a) for canonical, alist in ALIAS_GROUPS.items() for a in alist]
    for canonical, alias in sorted(all_aliases, key=lambda t: -len(t[1])):
        if alias in s_low:
            return canonical

    # Strip legal suffixes for cleanup
    cleaned = s
    for suffix in [", inc.", ", inc", ", ltd.", ", ltd", ", llc", ", plc",
                    ", corp.", ", corporation", " and company", " ag", " s.p.a.",
                    " s.p.r.l.", " srl", " gmbh", " kgaa", " s.a.",
                    " co., ltd.", " co. ltd", " (u.s.)", " limited", " pvt. ltd."]:
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[:-len(suffix)].rstrip(",. ")
            break
    return cleaned


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.sponsor_name AS raw, p.drug_id,
                   (po.approved_us OR po.approved_ex_us) AS approved
            FROM preclin.program p
            JOIN preclin.program_outcome po ON po.program_id = p.program_id
            JOIN preclin.drug d ON d.drug_id = p.drug_id
            WHERE d.is_placebo IS NOT TRUE AND p.sponsor_name IS NOT NULL
        """)
        rows = cur.fetchall()
    conn.close()

    per_sponsor = defaultdict(lambda: {"drugs": set(), "approved_drugs": set(), "variants": set()})
    for r in rows:
        canonical = normalize_sponsor(r["raw"])
        per_sponsor[canonical]["drugs"].add(r["drug_id"])
        per_sponsor[canonical]["variants"].add(r["raw"])
        if r["approved"]:
            per_sponsor[canonical]["approved_drugs"].add(r["drug_id"])

    with open("/tmp/sponsor_success_canonical.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["sponsor", "n_unique_drugs", "n_approved_drugs", "success_pct", "n_variants"])
        for name, d in sorted(per_sponsor.items(), key=lambda x: -len(x[1]["drugs"])):
            n = len(d["drugs"])
            appr = len(d["approved_drugs"])
            pct = 100 * appr / n if n else 0
            w.writerow([name, n, appr, round(pct, 1), len(d["variants"])])
    print(f"Wrote {len(per_sponsor)} canonical sponsors")

    # Verify key cases
    for check in ["Merck (MSD)", "UCB", "BridgeBio Pharma", "Pfizer", "GlaxoSmithKline (GSK)",
                   "Eli Lilly", "Novartis", "Bristol Myers Squibb", "Regeneron"]:
        d = per_sponsor.get(check)
        if d:
            print(f"  {check:<40} n={len(d['drugs']):>4}  appr={len(d['approved_drugs']):>3}  "
                   f"({100*len(d['approved_drugs'])/len(d['drugs']):.1f}%)  variants={len(d['variants'])}")

    # Filtered top 30
    filtered = sorted(
        [(n, d) for n, d in per_sponsor.items() if len(d["drugs"]) >= 15],
        key=lambda x: -(len(x[1]["approved_drugs"]) / max(1, len(x[1]["drugs"])))
    )
    print(f"\nTop 30 filtered (≥15 programs, qualifying pool: {len(filtered)}):")
    for name, d in filtered[:30]:
        n = len(d["drugs"])
        appr = len(d["approved_drugs"])
        print(f"  {name:<40} n={n:>4}  appr={appr:>3}  ({100*appr/n:.1f}%)")


if __name__ == "__main__":
    main()
