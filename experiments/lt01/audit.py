import csv
import io
import json
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from jsonschema import validate

FIELDS={'orders':'id order amount date status','payments':'id order amount','shipments':'id order status',
        'refunds':'id order amount','tickets':'id order message'}
def parse(raw):
    tables={}
    for name,fields in FIELDS.items():
        if name=='tickets':
            rows=json.loads(raw['tickets.json'])
        else:
            reader=csv.DictReader(io.StringIO(raw[name+'.csv']),strict=True)
            if reader.fieldnames!=fields.split():raise ValueError('BAD_HEADER_'+name)
            rows=list(reader)
        if not isinstance(rows,list):raise ValueError('BAD_TABLE')
        for r in rows:
            if set(r)!=set(fields.split()) or any(not isinstance(v,str) or not v.strip() for v in r.values()):
                raise ValueError('BAD_ROW_'+name)
        tables[name]=rows
    return tables

def normalize(tables):
    clean={};issues=[]
    for table,rows in tables.items():
        seen={};clean[table]=[]
        for row in rows:
            r={k:v.strip() for k,v in row.items()}
            r['order']=r['order'].upper()
            if not re.fullmatch('O[0-9]{4}',r['order']):raise ValueError('INVALID_ORDER_REF')
            if r['id'] in seen:
                if seen[r['id']]!=row:raise ValueError('CONFLICTING_RECORD_ID')
                issues.append(dict(order=r['order'],kind='duplicate_'+{'orders':'order','refunds':'refund'}.get(table,table),evidence=[r['id']],detail='相同记录ID及内容出现两次，仅计一次'))
                continue
            seen[r['id']]=row
            if 'amount' in r:
                if not re.fullmatch(r'[0-9]+\.\d{2}',r['amount']):
                    issues.append(dict(order=r['order'],kind='invalid_'+{'payments':'payment'}.get(table,table),evidence=[r['id']],detail='非法金额 '+r['amount']));continue
                r['amount']=int(Decimal(r['amount'])*100)
            if 'date' in r:r['date']=datetime.strptime(r['date'],'%Y/%m/%d').date().isoformat()
            if 'status' in r:
                r['status']=r['status'].lower()
                if r['status'] not in ({'open'} if table=='orders' else {'delivered','in_transit'}):raise ValueError('BAD_STATUS')
            clean[table].append(r)
    return {'tables':clean,'issues':issues}

def reconcile(data):
    tables=data['tables'];issues=data['issues'];rows=[];tickets=[]
    grouped=defaultdict(lambda:defaultdict(list))
    for table,items in tables.items():
        for item in items:grouped[item['order']][table].append(item)
    for oid,parts in sorted(grouped.items()):
        if len(parts['orders'])!=1:raise ValueError('ORDER_JOIN_AMBIGUOUS')
        order=parts['orders'][0];amount=order['amount']
        paid=sum(p['amount'] for p in parts['payments']);refund=sum(r['amount'] for r in parts['refunds'])
        ships=parts['shipments'];ids=lambda tab:[r['id'] for r in parts[tab]]
        def flag(kind,refs,detail):
            issues.append(dict(order=oid,kind=kind,evidence=[order['id']]+refs,detail=detail))
        if not parts['payments']:flag('missing_payment',[],'无有效支付记录')
        elif paid!=amount:flag('amount_mismatch',ids('payments'),f'订单 {amount} 分，实付 {paid} 分')
        if refund>paid:flag('over_refund',ids('payments')+ids('refunds'),f'退款 {refund} 分超过实付 {paid} 分')
        if paid and not ships:flag('unshipped',ids('payments'),'已付款，发货记录为空')
        if len(ships)>1:flag('multiple_shipments',ids('shipments'),f'{len(ships)} 条物流记录，须核对是否分包')
        for t in parts['tickets']:
            flag('complaint',[t['id']]+ids('shipments'),t['message'])
            tickets.append(dict(ticket=t['id'],message=t['message'],tracking=[r['status'] for r in ships]))
        rows.append(dict(order=oid,amount=amount,paid=paid,refund=refund,shipments=len(ships)))
    return dict(rows=rows,issues=issues,tickets=tickets)

def prompt(tickets):
    return ('分析以下模拟投诉。只输出 JSON 数组，每张工单一项。字段 ticket 为原工单号，category 只能为 conflict（客户与物流记录矛盾）或 uncertain（信息不充分），priority 只能为 high 或 normal，action 是一句中文核查建议。不要判责或承诺退款。\n'
            +json.dumps(tickets,ensure_ascii=False,separators=(',',':')))

def adjudicate(raw,tickets):
    fence=re.fullmatch(r'```json\s*\n(.*?)\n```',raw.strip(),re.S)
    def unique(pairs):
        data=dict(pairs)
        if len(data)!=len(pairs):raise ValueError('DUPLICATE_JSON_KEY')
        return data
    answers=json.loads(fence.group(1) if fence else raw,object_pairs_hook=unique)
    fields={'ticket':{'type':'string'},'category':{'enum':['conflict','uncertain']},'priority':{'enum':['high','normal']},
            'action':{'type':'string','minLength':2,'maxLength':200}}
    validate(answers,{'type':'array','items':{'type':'object','properties':fields,'additionalProperties':False,'required':list(fields)}})
    if sorted(r['ticket'] for r in answers)!=sorted(t['ticket'] for t in tickets):raise ValueError('TICKET_COVERAGE')
    return answers

