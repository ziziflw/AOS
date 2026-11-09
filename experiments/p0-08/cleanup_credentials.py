"""Delete only fixture targets explicitly receipted under this experiment's evidence."""
from boot import HERE,read
from credentials import Vault
import win32cred
import pywintypes
def cleanup():
    deleted=[]
    for p in (HERE/'evidence').rglob('owned-credential.json'):
        alias=read(p)['alias']
        if not alias.startswith('fixture-') or len(alias)!=40 or any(c not in '0123456789abcdef' for c in alias[8:]):raise ValueError('Invalid owned receipt')
        try:win32cred.CredDelete(Vault.prefix+alias,win32cred.CRED_TYPE_GENERIC,0);deleted.append(str(p))
        except pywintypes.error as exc:
            if exc.winerror!=1168:raise
    return deleted
if __name__=='__main__':print('Deleted owned fixture targets:',len(cleanup()))
