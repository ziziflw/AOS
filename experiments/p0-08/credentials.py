"""E3 owned aliases only; never enumerate user credentials or inspect environment keys."""
import uuid
from boot import ContractError

class Vault:
    prefix='AOS/P0-08/Synthetic/'
    def __init__(self):self.owned={}
    def create_fixture(self,alias=None):
        import win32cred
        alias=alias or 'fixture-'+uuid.uuid4().hex
        if not alias.startswith('fixture-') or not all(c in '0123456789abcdef-' for c in alias[8:]):raise ContractError('FIXTURE_ALIAS_INVALID')
        target=self.prefix+alias
        secret='fixture-secret-'+uuid.uuid4().hex
        win32cred.CredWrite({'Type':win32cred.CRED_TYPE_GENERIC,'TargetName':target,'CredentialBlob':secret,'Persist':win32cred.CRED_PERSIST_SESSION,'UserName':'AOS synthetic fixture'},0)
        self.owned[alias]=target
        return alias
    def resolve(self,alias):
        import win32cred
        if alias not in self.owned:raise ContractError('CREDENTIAL_ALIAS_UNBOUND')
        blob=win32cred.CredRead(self.owned[alias],win32cred.CRED_TYPE_GENERIC,0)['CredentialBlob']
        return blob.decode('utf-16-le') if isinstance(blob,bytes) else blob
    def close(self):
        import win32cred
        for target in self.owned.values():win32cred.CredDelete(target,win32cred.CRED_TYPE_GENERIC,0)
        self.owned.clear()
