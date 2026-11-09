"""Single-controller SQLite snapshot + event transaction; experimental only."""
from copy import deepcopy
from pathlib import Path
import json, os, sqlite3, time
from common import ContractError, digest, dumps

class ControllerLock:
    """OS-specific ownership isolated here; never written into workflow JSON."""
    def __init__(self,path):
        self.file=open(path,"a+b")
        self.file.seek(0,2)
        if not self.file.tell(): self.file.write(b"0"); self.file.flush()
        self.file.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close(); raise ContractError("CONTROLLER_ALREADY_OWNED")
    def close(self):
        if not self.file.closed:
            self.file.seek(0)
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            self.file.close()

class StateStore:
    def __init__(self,path,hook=None):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=ControllerLock(str(path)+".lock"); self.hook=hook
        try:
            self.db=sqlite3.connect(path,isolation_level=None)
            self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshot(id INTEGER PRIMARY KEY CHECK(id=1),seq INTEGER NOT NULL,state TEXT NOT NULL,checksum TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,event TEXT NOT NULL);
            """)
        except BaseException:
            self.lock.close(); raise
    def load(self):
        row=self.db.execute("SELECT seq,state,checksum FROM snapshot WHERE id=1").fetchone()
        if not row: return None
        seq,body,checksum=row; state=json.loads(body)
        if digest(state)!=checksum or state["seq"]!=seq: raise ContractError("SNAPSHOT_CORRUPT")
        eventseq=self.db.execute("SELECT coalesce(max(seq),0) FROM events").fetchone()[0]
        if eventseq!=seq: raise ContractError("EVENT_SNAPSHOT_DIVERGENCE")
        return state
    def commit(self,state,event):
        candidate=deepcopy(state)
        expected=candidate["seq"]; candidate["seq"]=expected+1
        event={"seq":expected+1,"monotonicNs":time.monotonic_ns(),"utcEpoch":time.time(),**deepcopy(event)}
        try:
            self.db.execute("BEGIN IMMEDIATE")
            row=self.db.execute("SELECT seq FROM snapshot WHERE id=1").fetchone()
            if (row[0] if row else 0)!=expected: raise ContractError("STALE_CONTROLLER")
            self.db.execute("INSERT OR REPLACE INTO snapshot VALUES(1,?,?,?)",(candidate["seq"],dumps(candidate),digest(candidate)))
            self.db.execute("INSERT INTO events VALUES(?,?)",(event["seq"],dumps(event)))
            if self.hook: self.hook("before_commit",event)
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction: self.db.execute("ROLLBACK")
            raise
        if self.hook: self.hook("after_commit",event)
        return candidate
    def events(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT event FROM events ORDER BY seq")]
    def close(self):
        self.db.close(); self.lock.close()

