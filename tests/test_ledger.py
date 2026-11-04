from datetime import datetime,timezone
from pathlib import Path
import json, sqlite3, subprocess, sys
import pytest
from relic_community import ContinuityLedger, Observer, ValidationError

FIXED=datetime(2026,11,3,12,0,tzinfo=timezone.utc)

def make(tmp_path):
    l=ContinuityLedger(tmp_path/'e.db',clock=lambda:FIXED)
    return l

def append(l,**changes):
    d={'project':'grimoire','actor':'test_runner','kind':'OBSERVATION','state':'OBSERVED',
       'source_ref':'opaque:test-fixture','summary':'Local metadata only'}
    d.update(changes)
    return l.append(**d)

def test_empty_chain(tmp_path):
    o=make(tmp_path).observer(); report=o.verify()
    assert report.ok and report.checked==0 and report.head_hash=='0'*64

def test_receipt_non_canonical(tmp_path):
    r=append(make(tmp_path)); assert r.sequence==1 and r.authority=='NON_CANONICAL' and len(r.entry_hash)==64

def test_chain_linkage(tmp_path):
    l=make(tmp_path); a=append(l); b=append(l,summary='Second run')
    assert b.sequence==2 and b.previous_hash==a.entry_hash and l.observer().verify().ok

def test_persists_reopen(tmp_path):
    l=make(tmp_path); append(l)
    assert ContinuityLedger(l.path).observer().verify().checked==1

def test_no_update_trigger(tmp_path):
    l=make(tmp_path); append(l)
    with sqlite3.connect(l.path) as c, pytest.raises(sqlite3.DatabaseError):
        c.execute('UPDATE events SET state=? WHERE sequence=1',('PASS',))

def test_no_delete_trigger(tmp_path):
    l=make(tmp_path); append(l)
    with sqlite3.connect(l.path) as c, pytest.raises(sqlite3.DatabaseError):
        c.execute('DELETE FROM events WHERE sequence=1')

def test_observer_no_writer(tmp_path):
    o=make(tmp_path).observer(); assert not hasattr(o,'append')

def test_readonly_db(tmp_path):
    l=make(tmp_path);append(l);o=l.observer()
    with o._connect() as c,pytest.raises(sqlite3.OperationalError):
        c.execute('INSERT INTO events(project) VALUES (?)',('x',))

def test_pack_hides_notes(tmp_path):
    l=make(tmp_path);append(l,summary='Non-sensitive note')
    p=l.observer().context_pack('grimoire'); assert p['authority']=='NON_CANONICAL'
    assert 'Non-sensitive note' not in json.dumps(p) and len(p['runes'])==1

def test_pack_project_scope(tmp_path):
    l=make(tmp_path);append(l,project='A');append(l,project='B')
    assert len(l.observer().context_pack('A')['runes'])==1
    assert l.observer().context_pack('A')['runes'][0]['source_ref']=='opaque:test-fixture'

def test_pack_bounded(tmp_path):
    l=make(tmp_path)
    for i in range(5):append(l,summary=f'Run {i}')
    r=l.observer().context_pack('grimoire',limit=2)['runes'];assert [e['sequence'] for e in r]==[5,4]

@pytest.mark.parametrize('limit',[0,51,-1,True,1.2])
def test_bad_limits(tmp_path,limit):
    with pytest.raises(ValidationError):make(tmp_path).observer().context_pack('grimoire',limit=limit)

@pytest.mark.parametrize('changes',[
 {'project':'../../escape'}, {'actor':''}, {'kind':'CANON'}, {'state':'SUCCESS'},
 {'source_ref':'https://secret.example/path'}, {'summary':'email@test.com'},
 {'summary':'secret api_key'}, {'evidence_sha256':'1234'},
])
def test_reject_bad_values(tmp_path,changes):
    with pytest.raises(ValidationError):append(make(tmp_path),**changes)

def test_bad_timestamp(tmp_path):
    l=ContinuityLedger(tmp_path/'x.db',clock=lambda:datetime(2026,11,3))
    with pytest.raises(ValidationError):append(l)

def test_read_get(tmp_path):
    l=make(tmp_path);append(l)
    v=l.observer().get_event(1);assert v['event']['authority']=='NON_CANONICAL'
    assert v['event']['summary']=='Local metadata only'
    assert l.observer().get_event(33) is None

def test_search_by_kind(tmp_path):
    l=make(tmp_path);append(l,kind='TEST_RESULT',state='PASS');append(l,kind='OBSERVATION')
    res=l.observer().search('grimoire','TEST_RESULT');assert len(res['matches'])==1
    assert res['matches'][0]['state']=='PASS'

def test_integrity_tamper_detect(tmp_path):
    l=make(tmp_path);append(l);append(l)
    # Simulate an attacker with DB administration rights bypassing triggers.
    with sqlite3.connect(l.path) as c:
        c.execute('DROP TRIGGER no_event_update')
        c.execute("UPDATE events SET entry_hash=? WHERE sequence=1",('a'*64,))
    r=l.observer().verify(); assert not r.ok and r.failure_sequence==1

def test_integrity_loss_detect(tmp_path):
    l=make(tmp_path);append(l);append(l)
    with sqlite3.connect(l.path) as c:
        c.execute('DROP TRIGGER no_event_delete')
        c.execute('DELETE FROM events WHERE sequence=1')
    assert not l.observer().verify().ok

def test_never_promotes_decision(tmp_path):
    l=make(tmp_path);append(l,kind='DECISION_RECORD',state='OBSERVED')
    p=l.observer().get_event(1)
    assert p['authority']==p['event']['authority']=='NON_CANONICAL'

def test_cli_smoke(tmp_path):
    cmd=[sys.executable,'-m','relic_community.cli','--db',str(tmp_path/'cli.db'),'init']
    out=subprocess.run(cmd,capture_output=True,text=True,check=True)
    assert json.loads(out.stdout)['ready']

def test_no_network_dependency(tmp_path,monkeypatch):
    import socket
    def forbid(*args,**kwargs): raise AssertionError('Unexpected network access')
    monkeypatch.setattr(socket.socket,'connect',forbid)
    l=make(tmp_path); append(l); assert l.observer().verify().ok


def test_malformed_payload_is_integrity_failure(tmp_path):
    l=make(tmp_path);append(l)
    with sqlite3.connect(l.path) as c:
        c.execute('DROP TRIGGER no_event_update')
        c.execute("UPDATE events SET payload=? WHERE sequence=1",('{broken',))
    result=l.observer().verify()
    assert not result.ok and result.failure_sequence==1


def test_append_order_persists_multiple_projects(tmp_path):
    l=make(tmp_path)
    a=append(l,project='A');b=append(l,project='B');c=append(l,project='A')
    assert [a.sequence,b.sequence,c.sequence]==[1,2,3]
    assert [r['sequence'] for r in l.observer().context_pack('A')['runes']]==[3,1]
    assert l.observer().verify().ok


def test_private_file_mode(tmp_path):
    import os, stat
    l=make(tmp_path)
    if os.name=='posix':
        assert stat.S_IMODE(l.path.stat().st_mode)==0o600


def test_corrupted_ledger_refuses_append(tmp_path):
    l=make(tmp_path); append(l)
    with sqlite3.connect(l.path) as c:
        c.execute('DROP TRIGGER no_event_update')
        c.execute("UPDATE events SET entry_hash=? WHERE sequence=1",('0'*64,))
    with pytest.raises(ValidationError): append(l)


def test_public_contribution_contract():
    from pathlib import Path
    import json
    root=Path(__file__).resolve().parents[1]
    tasks=json.loads((root/'CONTRIBUTION_TASKS.json').read_text())
    assert tasks['license']=='Apache-2.0'
    assert len({t['id'] for t in tasks['tasks']})==len(tasks['tasks'])
    assert 'canon' in tasks['canon_policy'].lower()
