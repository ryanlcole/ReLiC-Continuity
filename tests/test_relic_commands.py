"""Synthetic-only public command interface. All database reads are local."""
import sqlite3
from relic_community.agent_observer import AgentObserver
from relic_community.ledger import ContinuityLedger
from relic_community.relic_commands import dispatch_command


def fixture(tmp_path):
    ledger = ContinuityLedger(tmp_path / 'public-fixture.sqlite3')
    ledger.append(project='demo', actor='fixture', kind='OBSERVATION',
                  state='OBSERVED', source_ref='opaque:synthetic',
                  summary='Synthetic observation only')
    ledger.append(project='other', actor='fixture', kind='OBSERVATION',
                  state='OBSERVED', source_ref='opaque:other-project',
                  summary='Other project should not appear')
    return ledger, AgentObserver(ledger.path, 'demo')


def test_help_and_aliases_are_bounded_and_case_insensitive(tmp_path):
    _, obs = fixture(tmp_path)
    help_result = dispatch_command('  @ReLiC  HeLp  ', obs)
    assert help_result['status'] == 'OK'
    assert help_result['automated_write'] is False
    assert help_result['remote_service'] == 'NOT_CHECKED'
    assert 'Save' not in help_result['supported']
    assert dispatch_command('@relic', obs)['status'] == 'OK'
    assert dispatch_command('@RELIC CONTINUE', obs)['status'] == 'OK'
    assert dispatch_command('@ReLiC relic', obs)['status'] == 'OK'


def test_continue_returns_only_configured_project_and_no_summary(tmp_path):
    _, obs = fixture(tmp_path)
    for command in ('Continue', 'Load', 'relic'):
        result = dispatch_command('@ReLiC ' + command, obs)
        assert result['status'] == 'OK'
        assert result['context']['project'] == 'demo'
        assert len(result['context']['runes']) == 1
        assert 'other-project' not in str(result)
        assert 'Synthetic observation only' not in str(result)
        assert result['project_canon'] == 'NOT_CHECKED'


def test_status_and_checkup_report_local_integrity_only(tmp_path):
    _, obs = fixture(tmp_path)
    for cmd in ('Status', 'Checkup'):
        result = dispatch_command('@ReLiC ' + cmd, obs)
        assert result['status'] == 'OK'
        assert result['local_chain']['ok'] is True
        assert result['external_connections'] == 'UNKNOWN'
        assert result['deployment'] == 'NOT_CHECKED'
        assert len(result['context']['runes']) == 1


def test_verify_only_local_chain_never_validates_arbitrary_claims(tmp_path):
    _, obs = fixture(tmp_path)
    report = dispatch_command('@ReLiC Verify chain', obs)
    assert report['status'] == 'PASS'
    assert report['guarantee'] == 'LOCAL_HASH_CONSISTENCY_ONLY_NOT_FACTUAL_TRUTH'
    assert dispatch_command('@ReLiC Verify person-is-owner', obs)['status'] == 'UNKNOWN'


def test_trace_known_kind_and_reject_unknown_kind(tmp_path):
    _, obs = fixture(tmp_path)
    result = dispatch_command('@ReLiC Trace OBSERVATION', obs)
    assert result['status'] == 'OK'
    assert len(result['result']['matches']) == 1
    assert result['result']['matches'][0]['source_ref'] == 'opaque:synthetic'
    assert dispatch_command('@ReLiC Trace USER_PII', obs)['status'] == 'UNKNOWN'


def test_no_server_or_owner_mutations_via_text_commands(tmp_path):
    _, obs = fixture(tmp_path)
    before = obs.verify_chain()['checked']
    for cmd in ('Save', 'Amend deploy', 'Quit', 'Pause', 'Resume',
                'Next', 'Handoff', 'Smile', 'Idea change-authority'):
        result = dispatch_command('@ReLiC ' + cmd, obs)
        assert result['status'] == 'UNAVAILABLE'
        assert result['automated_write'] is False
    assert obs.verify_chain()['checked'] == before


def test_bad_input_does_not_echo_secrets(tmp_path):
    _, obs = fixture(tmp_path)
    for command in ('@ReLiC\nSave', '@ReLiC ' + 'A'*241, '@Other Help',
                    '@ReLiC Unknown super-secret', '@ReLiC Status password'):
        result = dispatch_command(command, obs)
        assert result['status'] in ('INVALID_COMMAND', 'UNKNOWN_COMMAND', 'UNSUPPORTED_ARGUMENT')
        assert 'super-secret' not in str(result) and 'password' not in str(result)


def test_corrupted_ledger_prevents_command_reads(tmp_path):
    ledger, obs = fixture(tmp_path)
    with sqlite3.connect(ledger.path) as conn:
        conn.execute('DROP TRIGGER no_event_update')
        conn.execute("UPDATE events SET entry_hash=? WHERE sequence=1", ('f'*64,))
    status = dispatch_command('@ReLiC Status', obs)
    assert status['status'] == 'INTEGRITY_FAILURE'
    assert status['records_disclosed'] == 0
    assert 'context' not in status
    for cmd in ('Continue', 'Trace OBSERVATION'):
        body = dispatch_command('@ReLiC ' + cmd, obs)
        obj = body.get('context') or body.get('result')
        assert obj['status'] == 'INTEGRITY_FAILURE'
        assert obj['records_disclosed'] == 0
        assert 'runes' not in obj and 'matches' not in obj
