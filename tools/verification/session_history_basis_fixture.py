"""Deterministic actual Core projection bytes for consumer compatibility.

Inputs are synthetic already-admitted storage rows. This does not prove their
source admission, a generator, installed HA, client rendering or audible output.
"""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path('examples/client_contracts/session_conversation_history/retention-bases-v2-touch-20261019.json')


def build():
    from custom_components.djconnect import session_history_projection as projection
    from custom_components.djconnect.session_speech import retained_projection
    stamp, until = '2026-10-18T12:00:00+00:00', '2027-01-16T12:00:00+00:00'
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026,10,18,12,0,tzinfo=UTC)
    common = {'moment_type':'album','persona':'radio_dj','persona_revision':0,
              'mood':'chill','locale':'en','summary':'Synthetic album',
              'text':'A synthetic retained contribution for contract decoding.'}
    cc0 = {'provider':'MusicBrainz','url':'https://musicbrainz.org/artist/00000000-0000-0000-0000-000000000001','license':'CC0-1.0'}
    spotify = {'provider':'Spotify','url':'https://open.spotify.com/album/'+'A'*22,'license':'Spotify metadata display'}
    wiki = {'provider':'Wikipedia','url':'https://en.wikipedia.org/wiki/Example',
            'license':'CC-BY-SA-4.0','revision_url':'https://en.wikipedia.org/w/index.php?oldid=1'}
    bodies = [
        {**common,'archive_basis':'cc0_normalized_fields_v1','source_attribution':cc0},
        {**common,'moment_type':'session','archive_basis':'runtime_authored_direction_v1','source_attribution':{}},
        {**common,'archive_basis':'owner_metadata_narration_v1','source_attribution':spotify,
         'provider':'Spotify','source_context':{'internal':'MUST_NOT_ESCAPE'},
         'session_media_reference':{'internal':'MUST_NOT_ESCAPE'}},
        {**common,'moment_type':'artist','archive_basis':'public_artist_narration_v1',
         'source_attribution':wiki,'sources':[{**wiki,'kind':'source','language':'en'}, {**cc0,'kind':'source'}],
         'qualified_fact_attribution':cc0,'qualified_fact_text':'Synthetic public normalized fact.',
         'dialogue_subjects':[{'name':'Synthetic artist','role':'Group'}]},
        {'moment_type':'album','content_state':'unavailable','unavailable_reason':'source_retention_not_qualified',
         'text':'MUST_NOT_ESCAPE','audio_url':'MUST_NOT_ESCAPE','artwork_url':'MUST_NOT_ESCAPE','source_attribution':spotify},
        {'moment_type':'silence','content_state':'silence','text':'MUST_NOT_ESCAPE','reason':'MUST_NOT_ESCAPE'},
    ]
    rows, entries = [], []
    with patch.object(projection,'datetime',Clock):
        for index, body in enumerate(bodies,1):
            body = {**body,'moment_id':'moment-basis-'+str(index)}
            row = {'entry_id':'entry-basis-'+str(index),'session_id':'session-basis-contract',
                'order':index,'kind':'dj_moment' if index<=4 else 'dj_publication' if index==5 else 'dj_silence',
                'occurred_at':stamp,'retained_until':until,'visibility':'owner','revoked_at':'',
                'body':json.dumps(body)}
            rows.append(row)
            entry = projection.project_entry(row)
            assert entry is not None
            if entry['kind']=='dj_moment':
                entry['session_speech'] = retained_projection(entry)
            entries.append(entry)
        withdrawn_body = projection.publication_receipt(json.loads(rows[2]['body']),'source_withdrawn')
        withdrawn = projection.project_entry({**rows[2],'kind':'dj_publication','body':json.dumps(withdrawn_body)})
        negative = {}
        for name, changes in {
            'unknown_basis':{'body':json.dumps({**common,'archive_basis':'future_unqualified_basis'})},
            'expired':{'retained_until':'2026-10-17T12:00:00+00:00'},
            'revoked':{'revoked_at':stamp},
            'shared_visibility':{'visibility':'shared'},
        }.items():
            negative[name] = projection.project_entry({**rows[0],**changes}) is None
    page = {'success':True,'schema_version':1,
        'session':{'session_id':'session-basis-contract','lifecycle_status':'ACTIVE',
                   'created_at':stamp,'started_at':stamp,'ended_at':'','interrupted_at':'',
                   'revision':'basis-fixture-6','read_only':False,
                   'history_coverage':'saved_entries_only_no_retrospective_observations'},
        'entries':entries,'revision':'basis-fixture-6','next_cursor':None,
        'coverage':'bounded_saved_entry_window','window':'tail','anchor_entry_id':None,
        'scanned_order_min':1,'scanned_order_max':6,'scan_complete':True}
    paths = ('custom_components/djconnect/session_history_projection.py',
             'custom_components/djconnect/historical_projection_query.py',
             'custom_components/djconnect/session_speech.py')
    return {'qualification':'ACTUAL_CORE_PROJECTION_AND_SPEECH_DESCRIPTOR_FROM_SYNTHETIC_ADMITTED_ROWS_ONLY',
        'source_pins':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'tail_window':page,'withdrawn_same_identity':withdrawn,'refused_rows':negative,
        'installed':'NOT_RUN','native':'NOT_RUN','audible':'NOT_RUN'}


async def build_connected(service):
    """Real SQLite/query tail envelope; only already-admitted row inputs are fixtures."""
    from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.historical_projection_query import HistoricalProjectionQueryService
    from custom_components.djconnect import session_history_projection as projection
    from custom_components.djconnect.persistence import sessions as sessions_module
    from custom_components.djconnect.persistence import history as history_module
    from custom_components.djconnect.persistence import summary as summary_module
    from custom_components.djconnect.history_entry_contract import represent, HistoryEntryUpgradeRequired, upgrade_error
    template = build()
    stamp = '2026-10-18T12:00:00+00:00'
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026,10,18,12,0,tzinfo=UTC)
    owner, sid = 'fixture-history-owner', 'session-basis-contract'
    repository = HistoricalProjectionRepository(service)
    sessions = PersistentSessionRepository(service)
    query = HistoricalProjectionQueryService(repository)
    with patch.object(projection,'datetime',Clock), patch.object(history_module,'datetime',Clock), \
            patch.object(summary_module,'datetime',Clock), \
            patch.object(sessions_module,'_now',lambda:stamp):
        await sessions.async_create(owner,session_id=sid)
        await sessions.async_transition(owner,sid,'ACTIVE')
        entries = []
        for entry in template['tail_window']['entries']:
            body = {k:v for k,v in entry.items() if k not in {
                'entry_id','session_id','order','kind','occurred_at','retained_until',
                'historical_view_only','current_display_allowed','session_speech'}}
            entries.append({'kind':entry['kind'],'reference_id':entry['moment_id'],
                            'occurred_at':stamp,'body':body})
        await repository.async_append_entries(owner,sid,entries,authorize=lambda:True)
        page = await query.async_timeline_window(owner,sid,window='tail',limit=20)
        assert page['window_limit']==20 and len(page['entries'])==6
        try:
            represent(page,1)
        except HistoryEntryUpgradeRequired:
            legacy_error = upgrade_error()
        else:
            raise AssertionError('mixed page must require upgrade for original schema1')
        rows = await repository.async_entry_records(owner,sid)
        metadata = rows[2]
        withdrawn = projection.project_entry({**metadata,'kind':'dj_publication',
            'body':json.dumps(projection.publication_receipt(json.loads(metadata['body']),'source_withdrawn'))})
        current = represent(page,2)
    paths = (*template['source_pins'],'custom_components/djconnect/history_entry_contract.py')
    return {'qualification':'ACTUAL_SQLITE_QUERY_TAIL_AND_REPRESENTATION_FROM_SYNTHETIC_ADMITTED_ROWS',
        'source_pins':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'tail_window':current,'legacy_mixed_page':{'http_status':409,'body':legacy_error},
        'withdrawn_same_identity':withdrawn,'refused_rows':template['refused_rows'],
        'installed':'NOT_RUN','native':'NOT_RUN','audible':'NOT_RUN'}
