"""Local-only CLI. No HTTP endpoint, network calls, or external data transfer."""
from __future__ import annotations
import argparse, json
from .ledger import ContinuityLedger

def main() -> int:
    ap=argparse.ArgumentParser(description='ReLiC Community local reference implementation')
    ap.add_argument('--db',default='./relic-events.sqlite3',help='local SQLite file')
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    add=sub.add_parser('append')
    for option in ('project','actor','kind','state','source-ref','summary'):
        add.add_argument('--'+option,required=True)
    add.add_argument('--evidence-sha256')
    sub.add_parser('verify')
    pack=sub.add_parser('context')
    pack.add_argument('--project',required=True)
    pack.add_argument('--limit',type=int,default=10)
    show=sub.add_parser('get')
    show.add_argument('--sequence',type=int,required=True)
    args=ap.parse_args()
    ledger=ContinuityLedger(args.db)
    if args.command=='init': answer={'ready':True,'file':str(ledger.path)}
    elif args.command=='append':
        answer=ledger.append(project=args.project,actor=args.actor,kind=args.kind,
                             state=args.state,source_ref=args.source_ref,
                             summary=args.summary,evidence_sha256=args.evidence_sha256).__dict__
    elif args.command=='verify': answer=ledger.observer().verify().__dict__
    elif args.command=='context': answer=ledger.observer().context_pack(args.project,limit=args.limit)
    else: answer=ledger.observer().get_event(args.sequence)
    print(json.dumps(answer,indent=2,sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
