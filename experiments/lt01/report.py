"""Render verified C1 results and request timings; never drives C1 or makes a model request."""
from score import ROOT,authoritative,records,read
from collections import Counter
from pathlib import Path
import argparse,json

NAMES={'duplicate_order':'重复订单行','duplicate_refund':'重复退款行','amount_mismatch':'订单与支付金额不一致',
       'missing_payment':'缺少支付','over_refund':'退款超过实付','unshipped':'已支付未发货',
       'multiple_shipments':'多条物流记录','complaint':'客户投诉待核查','invalid_payment':'非法支付金额'}
def render(label):
    if not label.isalnum():raise ValueError('LABEL')
    d=ROOT/'runs'/label;s=authoritative(d)
    if s['state']!='succeeded':raise ValueError('RUN_NOT_SUCCESSFUL')
    result=json.loads(s['scopes']['main']['result']);target=d/'results'
    events=read(d/'events.json');wire=records(d);resp=next(e for e in wire if e['kind']=='received')
    approved=next(e['utcEpoch'] for e in events if e['kind']=='approval-resolved' and e['decision'])
    pending=next(e['utcEpoch'] for e in events if e['kind']=='approval-requested')
    end=events[-1]['utcEpoch'];review=approved-pending;total=end-s['createdAt']
    metrics=read(d/'execution-metrics.json')
    metrics.update(model='google/gemma-4-e4b',generationRequests=sum(e['kind']=='generate' for e in wire),modelConcurrency=1,
                   serviceUsage=resp['usage'],cacheTokens=(resp['usage'].get('prompt_tokens_details') or {}).get('cached_tokens'),
                   modelPostMs=resp['ms'],fromC1CreationToTerminalSec=total,approvalAndOfflineSec=review,
                   excludingApprovalSec=total-review,approvalCount=1,unplannedRepeatedAttempts=sum(max(0,i-1) for i in metrics['attempts'].values()))
    (target/'execution-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),'utf-8')
    flags=read(target/'exceptions.json');adv=read(target/'action-plan.json')
    with (target/'reconciliation.csv').open(encoding='utf-8') as f:count=sum(1 for _ in f)-1
    lines=['# 模拟电商审计报告','',f'运行 {s["runId"]}。核对 {count} 笔合成订单，发现 {len(flags)} 项异常候选，涉及 {len(set(v["order"] for v in flags))} 笔订单。金额单位为分。','','## 对账发现','',
           '|订单|发现|依据|记录 ID|','|---|---|---|---|']
    for v in sorted(flags,key=lambda v:v['order']):
        lines.append(f'|{v["order"]}|{NAMES[v["kind"]]}|{v["detail"]}|{", ".join(v["evidence"])}|')
    lines+=['','## 已确认可记录的核查建议','']
    for a in adv:lines.append(f'- {a["ticket"]}（{a["category"]}，{a["priority"]}）{a["action"]}')
    lines+=['','重复 ID 仅计一次。非法金额隔离。多条物流可能来自分包，投诉须结合签收凭证及客户说明复核。本次仅记录建议，未执行订单或款项操作。']
    (target/'audit-report.md').write_text('\n'.join(lines)+'\n','utf-8')
    print(label,metrics['serviceUsage'],round(metrics['modelPostMs']),round(total,3),round(total-review,3),round(review,3))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');render(p.parse_args().label)

