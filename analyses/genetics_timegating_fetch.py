"""Date the GWAS study PMIDs behind cohort targets' genome-wide-significant hits, so
GWAS genetic support can be time-gated to first-trial-date (same eutils-PMID method as
the literature date-cleaning). Writes data/gwas_pmid_year.csv (pmid, year). Resumable."""
import os, sys, time, json, urllib.request, urllib.parse, csv
import psycopg2
DB=os.environ["DATABASE_URL"]; EUTILS="https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUT="data/gwas_pmid_year.csv"
sys.path.insert(0,"benchmark"); from importlib import import_module; runner=import_module("runner")
c=psycopg2.connect(DB); cur=c.cursor()
rows=runner.load_cohort(c,min_phase=2); tids=tuple(sorted({r["target_id"] for r in rows}))
cur.execute("""SELECT DISTINCT study_pmid FROM public.gwas_associations
  WHERE target_id IN %s AND p_value<=5e-8 AND study_pmid ~ '^[0-9]+$'""",(tids,))
pmids=[r[0] for r in cur.fetchall()]; c.close()
done={}
if os.path.exists(OUT):
    for r in csv.DictReader(open(OUT)): done[r["pmid"]]=r["year"]
todo=[p for p in pmids if p not in done]
print(f"{len(pmids)} GWAS PMIDs; {len(done)} cached; {len(todo)} to fetch")
def esum(batch):
    url=f"{EUTILS}/esummary.fcgi?db=pubmed&retmode=json&id={','.join(batch)}"
    try: return json.load(urllib.request.urlopen(url,timeout=60)).get("result",{})
    except Exception as e: print("  err",str(e)[:60]); return {}
for i in range(0,len(todo),150):
    batch=todo[i:i+150]; res=esum(batch)
    for p in batch:
        d=res.get(p,{}); yr=(d.get("pubdate","") or d.get("epubdate","") or "")[:4]
        done[p]=yr if yr.isdigit() else ""
    with open(OUT,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["pmid","year"])
        for k,v in done.items(): w.writerow([k,v])
    print(f"  ...{min(i+150,len(todo))}/{len(todo)}"); time.sleep(0.4)
print(f"wrote {OUT}: {sum(1 for v in done.values() if v)} dated / {len(done)}")
