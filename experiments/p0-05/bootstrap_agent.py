"""Shared paths/declarations. Never import the Agent service into the engine."""
import sys,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P03=HERE.parent/'p0-03';P04=HERE.parent/'p0-04'
sys.path.insert(0,str(P03))
from common import read,write,digest,dumps,ContractError,OutcomeError
SDK='1.2.3';SPEC='1.0.1';WIRE='1.0'
SECRET='P05_SYNTHETIC_SECRET_DO_NOT_LOG'
def redact(v):
    if isinstance(v,str): return v.replace(SECRET,'[REDACTED]')
    if isinstance(v,list): return [redact(x) for x in v]
    if isinstance(v,dict): return {k:('[REDACTED]' if re.search(r'authorization|password|api.?key|access.?token|secret',k,re.I) else redact(x)) for k,x in v.items()}
    return v
def jsonl(path,body):
    with Path(path).open('a',encoding='utf-8') as f: f.write(json.dumps(redact(body),ensure_ascii=False,allow_nan=False)+'\n')
