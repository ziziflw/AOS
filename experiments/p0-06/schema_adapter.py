"""Same Draft 2020-12 documents, no PowerShell execution-policy dependency."""
from copy import deepcopy
from jsonschema import Draft202012Validator
from common import read,check_references,digest,ContractError
class SchemaAdapter:
    def __init__(self,schema_path,catalog_path):
        self.schema=read(schema_path);self.defs={**self.schema['$defs'],**read(catalog_path)['types']};self.cache={}
        self.version='jsonschema 4.26.0 / Draft202012Validator'
    def validate(self,value,sub_schema=None,code='SCHEMA_INVALID'):
        check_references(value)
        if sub_schema is not None:check_references(sub_schema,schema=True)
        key=digest([value,sub_schema])
        if key not in self.cache:
            selected=self.schema if sub_schema is None else {'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':deepcopy(self.defs),**deepcopy(sub_schema)}
            self.cache[key]=Draft202012Validator(selected).is_valid(value)
        if not self.cache[key]:raise ContractError(code)
    def close(self):pass
