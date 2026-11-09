"""Experiment setup and evidence export, not runtime policy."""
from pathlib import Path
from copy import deepcopy
import json, shutil
from common import read, write
from contracts import Contracts, SchemaClient
from mocks import SyntheticSystem, MockRegistry
from runtime import Runtime
from store import StateStore
from fixtures import BASE,FIX,ROOT,HERE

class Session:
    def __init__(self,directory,validator,*,workflow=None,request=None,catalog_path=None,environment=None,plan=None,recover=False,hook=None,approval_ttl=300):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
        if not recover:
            write(self.directory/"workflow.json",workflow); write(self.directory/"request.json",request)
            write(self.directory/"environment.json",environment or read(FIX/"environment.json"))
            write(self.directory/"simulation-plan.json",plan or {})
            shutil.copyfile(catalog_path or FIX/"catalog.json",self.directory/"catalog.json")
        self.system=SyntheticSystem(self.directory/"synthetic-system.sqlite")
        self.registry=MockRegistry(self.system,read(self.directory/"simulation-plan.json"))
        self.store=None; self.runtime=None
        try:
            self.c=Contracts(read(self.directory/"workflow.json"),read(self.directory/"request.json"),self.directory/"catalog.json",validator,self.registry)
            self.store=StateStore(self.directory/"run.sqlite",hook)
            self.runtime=Runtime(self.c,self.store,self.registry,read(self.directory/"environment.json"),approval_ttl=approval_ttl)
        except BaseException:
            if self.store: self.store.close()
            self.system.close()
            raise
    def export(self,label="final"):
        if self.runtime:
            write(self.directory/(label+"-snapshot.json"),self.runtime.snapshot)
            write(self.directory/(label+"-events.json"),self.store.events())
            write(self.directory/(label+"-synthetic-system.json"),self.system.dump())
    async def close(self):
        if self.runtime:
            await self.runtime.close()
            self.export()
        if self.store: self.store.close()
        self.system.close()

def inputs(name):
    if name in ("a","b","c"):
        return read(BASE/("scenario-"+name+".workflow.json")),read(BASE/("scenario-"+name+".run-request.json")),BASE/"fixture-catalog.json"
    return read(FIX/(name+".workflow.json")),read(FIX/(name+".request.json")),FIX/"catalog.json"

async def approve_all(runtime):
    """Explicit trusted test operator; no approval automation inside Runtime."""
    for _ in range(30):
        state=await runtime.drive()
        if state["state"]!="waiting-approval": return state
        pending=[a for a in state["approvals"].values() if a["status"]=="pending"]
        if not pending: raise AssertionError("Waiting without a pending approval")
        for a in pending: runtime.approve(a["id"],a["fingerprint"],True)
    raise AssertionError("Test operator approval bound exceeded")

