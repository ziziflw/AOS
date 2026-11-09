"""Seeded fixtures and hidden expected ledger, generated from scenario assignments."""
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ('orders','payments','shipments','refunds','tickets')
FIELDS = dict(orders=['id','order','amount','date','status'], payments=['id','order','amount'],
              shipments=['id','order','status'], refunds=['id','order','amount'],tickets=['id','order','message'])

def dump(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')

def generate(size):
    rng=random.Random(17613+size)
    inputs=ROOT/'inputs'/str(size)
    inputs.mkdir(parents=True,exist_ok=True)
    rows={k:[] for k in FILES}
    answers={}
    picked=rng.sample(range(1,size+1), 10)
    for i in range(1,size+1):
        oid=f'O{i:04}'
        amount=rng.randrange(500,25000)
        case=picked.index(i) if i in picked else -1
        paid=0 if case==2 else amount+(125 if case==1 else 0)
        refund=amount+100 if case==3 else 150 if case==4 else 0
        ships=0 if case in (2,5) else 2 if case==6 else 1
        order={'id':f'Orow{i}','order':' '+oid.lower()+' ','amount':f'{amount/100:.2f}','date':'2026/10/01','status':' Open '}
        rows['orders'].append(order)
        if case==0: rows['orders'].append(order.copy())
        if paid: rows['payments'].append(dict(id=f'P{i}',order=oid,amount=f'{paid/100:.2f}'))
        for k in range(ships):
            rows['shipments'].append(dict(id=f'S{i}-{k}',order=oid,status='delivered' if case==7 else 'in_transit'))
        if refund:
            row=dict(id=f'R{i}',order=oid,amount=f'{refund/100:.2f}')
            rows['refunds'].append(row)
            if case==4: rows['refunds'].append(row.copy())
        if case in (7,8):
            message='页面显示签收，但我没有收到包裹。' if case==7 else '我可能选错了地址，也不确定包裹是否已到驿站，请核实。'
            rows['tickets'].append(dict(id=f'T{i}',order=oid,message=message))
        if case==9: rows['payments'].append(dict(id=f'X{i}',order=oid,amount='bad'))
        kinds=['duplicate_order','amount_mismatch','missing_payment','over_refund','duplicate_refund','unshipped','multiple_shipments','complaint','complaint','invalid_payment']
        answers[oid]=dict(amount=amount,paid=paid,refund=refund,shipments=ships,flags=[] if case<0 else [kinds[case]],
                          review={7:'conflict',8:'uncertain'}.get(case))
    for k,data in rows.items():
        rng.shuffle(data)
        if k=='tickets':dump(inputs/'tickets.json',data)
        else:
            with (inputs/(k+'.csv')).open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,FIELDS[k]);w.writeheader();w.writerows(data)
    oracle=ROOT/'oracle';oracle.mkdir(exist_ok=True)
    dump(oracle/f'{size}.json',answers)

if __name__=='__main__':
    for size in (30,200):generate(size)

