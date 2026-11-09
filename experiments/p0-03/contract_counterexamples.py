"""Read-only extraction of exact P0-02 descriptor ambiguities; no schema rewrite."""
from common import read, write
from fixtures import BASE, HERE

def main():
    c=read(BASE/"fixture-catalog.json")
    condition=next(d for d in c["nodeDefinitions"] if d["typeId"]=="core.condition")
    task=next(d for d in c["nodeDefinitions"] if d["typeId"]=="core.input.task")
    b=read(BASE/"scenario-b.workflow.json")
    records={"classification":"static counterexamples, not additional execution tests",
      "condition":{"descriptor":condition,"successfulSelectedOutput":["pass","done"],
                   "literalRequiredButAbsent":[p["id"] for p in condition["ports"] if p["direction"]=="output" and p["required"] and p["id"] not in ("pass","done")],
                   "problem":"Both mutually exclusive outputs cannot be universally required at runtime."},
      "successError":{"descriptor":task,"successfulSelectedOutput":["out","done"],
                      "literalRequiredButAbsent":[p["id"] for p in task["ports"] if p["direction"]=="output" and p["required"] and p["id"] not in ("out","done")],
                      "problem":"A successful input node must not manufacture an Error value to satisfy required=true."},
      "retryScope":{"rootPolicy":b["executionPolicy"],"nodePolicies":{n["id"]:n["policy"] for n in b["graph"]["nodes"]},
                    "problem":"Root maxAttempts=1/retryMode=never coexists with tool maxAttempts=2/retryMode=safe; inheritance/aggregation needs an explicit rule."},
      "prototypeRule":"Known versioned builtins activate output sets by outcome; root retry controls whole-run replay, node retry controls attempts. Provisional interpretation, not a schema migration."}
    write(HERE/"evidence/contract-counterexamples.json",records)
    print("Extracted P0-02 counterexamples without changing their source files.")

if __name__=="__main__": main()
