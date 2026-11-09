"""Import the existing experiments; no workflow scheduler is defined here."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for name in ('p0-03','p0-04','p0-05','p0-06'):
    sys.path.insert(0,str(HERE.parent/name))
from common import read,write,digest,ContractError,OutcomeError
