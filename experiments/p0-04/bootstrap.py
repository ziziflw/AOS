"""Import the unchanged P0-03 controller, not a second scheduler."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P03=HERE.parent/'p0-03'
sys.path.insert(0,str(P03))
from common import read,write,digest,ContractError,OutcomeError
PROTOCOL='2025-11-25'
SDK='1.30.0'
