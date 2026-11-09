"""Read-only delivery checks plus a new audit artifact; not runtime test counts."""
import hashlib, json, re, platform, time
from pathlib import Path
from common import read, write
from fixtures import HERE, ROOT

def main():
    allowed={"README.md","research/README.md","research/sources.md",
             "research/02-node-contracts/README.md","research/03-execution-engine/README.md",
             "research/10-feasibility-experiments/README.md"}
    checks=[]
    for row in read(HERE/"baseline-manifest.json"):
        p=Path(row["Path"]); name=p.relative_to(ROOT).as_posix()
        actual=hashlib.sha256(p.read_bytes()).hexdigest().upper()
        checks.append({"path":name,"before":row["Hash"],"after":actual,"changed":actual!=row["Hash"],
                       "allowedIndexUpdate":name in allowed,"passed":actual==row["Hash"] or name in allowed})
    suite=HERE/read(HERE/"evidence/latest.json")["directory"]
    hashes=read(suite/"source-hashes.json")
    source_checks=[{"path":name,"passed":hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected} for name,expected in hashes.items()]
    assertions=[]
    for p in suite.glob("test_*/assertions.json"):
        rows=read(p); assertions.append({"file":p.relative_to(HERE).as_posix(),"comparisons":len(rows),"passed":all(r["passed"] for r in rows)})
    docs=[ROOT/"README.md",ROOT/"research/README.md",ROOT/"research/sources.md",
          *(ROOT/name for name in sorted(allowed) if name not in {"README.md","research/README.md","research/sources.md"}),
          HERE/"README.md",*sorted((ROOT/"planning").glob("p0-03-*.md"))]
    broken=[]
    for p in docs:
        for target in re.findall(r"\]\(([^)]+)\)",p.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"): continue
            file=target.split("#",1)[0]
            if file and not (p.parent/file).exists(): broken.append({"document":p.relative_to(ROOT).as_posix(),"target":target})
    summary=read(suite/"summary.json")
    result={"classification":"delivery audit, separate from execution tests","environment":{"platform":platform.platform(),
            "clocks":{name:vars(time.get_clock_info(name)) for name in ("monotonic","perf_counter")}},"baselineFiles":len(checks),
            "unchangedBaselineFiles":sum(not x["changed"] for x in checks),"baseline":checks,
            "testedSourcesUnchanged":source_checks,"assertionFiles":assertions,"brokenLocalFileLinks":broken,
            "suite":{"testsRun":summary["testsRun"],"failures":summary["failures"],"errors":summary["errors"]}}
    result["passed"]=all(x["passed"] for x in checks+source_checks+assertions) and not broken and summary["testsRun"]==18 and summary["failures"]==summary["errors"]==0
    write(HERE/"evidence/delivery-audit.json",result)
    print(json.dumps({k:result[k] for k in ("passed","baselineFiles","unchangedBaselineFiles","brokenLocalFileLinks","suite")},ensure_ascii=False))
    return 0 if result["passed"] else 1

if __name__=="__main__": raise SystemExit(main())
