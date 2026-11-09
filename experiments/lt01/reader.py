"""Dedicated MCP stdio service. Only five fixed synthetic files, two dataset IDs."""
import os
from pathlib import Path
from typing import Literal
from mcp.server.fastmcp import FastMCP

ROOT=Path(__file__).resolve().parent/'inputs'
NAMES=('orders.csv','payments.csv','shipments.csv','refunds.csv','tickets.json')
server=FastMCP('LT01 synthetic audit inputs')

@server.tool()
def read_dataset(size:Literal['30','200']) -> dict[str,str]:
    if os.environ.get('LT01_FAULT')=='mcp-stop':
        os._exit(71)
    data={}
    for name in NAMES:
        p=ROOT/size/name
        if p.resolve()!=p or p.stat().st_size>200000:
            raise ValueError('INPUT_BOUNDARY')
        data[name]=p.read_text('utf-8-sig')
    return data

if __name__=='__main__':server.run(transport='stdio')

