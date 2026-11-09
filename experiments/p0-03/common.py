"""Shared JSON helpers; no workflow execution logic."""
from copy import deepcopy
from pathlib import Path
import hashlib, json, re

VERSION = "0.1.0-draft.1"
TERMINAL = {"succeeded", "failed", "cancelled", "skipped", "unknown"}
def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
def digest(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()
def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ContractError("DUPLICATE_JSON_KEY", key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
def pointer(value, path):
    if path == "": return value
    if not path.startswith("/"): raise ContractError("JSON_POINTER", path)
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value
class ContractError(ValueError):
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(code + (": " + str(message) if message else ""))
class OutcomeError(Exception):
    def __init__(self, code, *, retryable=False, side_effect="not-started"):
        self.code, self.retryable, self.side_effect = code, retryable, side_effect
        super().__init__(code)
def error_value(exc):
    return {"code": getattr(exc, "code", type(exc).__name__), "message": str(exc) or type(exc).__name__,
            "category": "validation" if isinstance(exc, ContractError) else "execution",
            "retryable": getattr(exc, "retryable", False), "sideEffect": getattr(exc, "side_effect", "not-started")}
def check_references(value, *, schema=False):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and (not isinstance(item, str) or not item.startswith("#/$defs/")):
                raise ContractError("REMOTE_SCHEMA_REFERENCE", item)
            if key == "resourceUri" and not schema:
                if not isinstance(item, str) or not re.fullmatch(r"(workspace|artifact|input):[A-Za-z0-9][A-Za-z0-9._/-]*", item):
                    raise ContractError("RESOURCE_URI", item)
                if ".." in item.split(":",1)[1].split("/") or "%" in item or "\\" in item:
                    raise ContractError("RESOURCE_TRAVERSAL", item)
            if re.fullmatch(r"api[_-]?key|authorization|password|access[_-]?token", key, re.I):
                raise ContractError("SECRET_FIELD_FORBIDDEN", key)
            check_references(item, schema=schema or key in ("inputSchema", "outputSchema", "configSchema", "parameterSchema", "types", "$defs"))
    elif isinstance(value, list):
        for item in value: check_references(item, schema=schema)

