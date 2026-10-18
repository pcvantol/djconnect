"""Paid expression pilot on the existing isolated real HA agent, not a release GO."""
import asyncio
import json
import os


async def run_albums(hass, runtime, manager, identity, headers, model_receipts):
    """Fixed eight real HA expressions and publications for the reported album.

    Retrieve one real public corpus then pin it unchanged for fair comparison.
    Production fresh-retrieval latency is a separate trial. Only current playback
    and household are synthetic. No installed/client/audible claim.
    """
    from pathlib import Path
    from dataclasses import asdict
    import hashlib
    from unittest.mock import patch
    from custom_components.djconnect.api_handlers import _connect_session_narration, _conversation_profile_fence
    from custom_components.djconnect.profile_context import async_resolve_device_bound_request_context
    from custom_components.djconnect.session_facts import catalog_facts
    from custom_components.djconnect.session_conversation import query_service
    from custom_components.djconnect.pipeline import realize_session_narration
    from custom_components.djconnect.session_runtime import DJPersona
    from scripts.verification.askdj_contextual_golden import ACTIVE_CASE

    rows = []
    catalog = {'uri':'spotify:track:'+'1'*22, 'title':'We Are - Symphonic Version',
        'artist':'HAEVN', 'artist_ids':['65Tmt9uAPTYGl1ZhsOeEJ6'],
        'album_name':'Symphonic Tales', 'album_uri':'spotify:album:3VSIVHxafHRMSs2SQB9nju',
        'release_date':'2020-04-03','release_date_precision':'day'}
    context = await async_resolve_device_bound_request_context(hass, runtime, identity,
        request_source='isolated-album-narration-diagnostic')
    from custom_components.djconnect import album_narration
    from custom_components.djconnect.ask_dj import public_research as research
    fact = catalog_facts(catalog)[0]
    async def guard():
        _conversation_profile_fence(hass,runtime,identity,headers,context)
    async with research.PublicFetch(guard) as fetch:
        public = await album_narration.public_identity(fetch,fact)
        assert public is not None, 'album_public_identity_unavailable'
        sources,state = await research.research(public[5],
            'Tell a documented story specifically about the album '+public[2]+' by '+public[5]+'.',
            'nl',guard,qualified_music=True,expected_roles=(public[6],),expected_entity_id=public[4],
            allow_web=False,fetch=fetch,original_paragraphs=True)
        assert sources, 'album_public_references_unavailable'
        source_requests = fetch.requests
    package = {'public_identity':public,'sources':[s.model_data() for s in sources],
        'public_source_records':[asdict(s) for s in sources],
        'local_source_fixture':asdict(fact),'actual_source_requests':source_requests}
    package_hash = hashlib.sha256(json.dumps(package,sort_keys=True).encode()).hexdigest()
    Path('/lab/album-public-evidence.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n')
    async def pinned_identity(owned, selected):
        await owned.guard()
        assert selected == fact
        return public
    async def pinned_sources(subject,question,locale,owned_guard,**kwargs):
        await owned_guard()
        assert subject == public[5] and kwargs['expected_entity_id'] == public[4]
        assert kwargs['allow_web'] is False
        return list(sources), state
    with patch.object(album_narration,'public_identity',pinned_identity), patch.object(research,'research',pinned_sources):
        for persona in ('home_dj','radio_dj','club_dj','festival_dj'):
            for mood in ('chill','party'):
                case = 'public-album-'+persona+'-'+mood+'-nl'
                token = ACTIVE_CASE.set(case)
                before = len(model_receipts)
                active = None
                debug = {}
                try:
                    active = await manager.async_start(owner_profile_id='profile-a',locale='nl',
                        selected_mood=mood,dj_persona=DJPersona(persona),music_backend='spotify_direct',
                        allowed_capability_intents=frozenset({'album_story'}))
                    _connect_session_narration(hass,runtime,context,active,identity,headers)
                    registration = manager._narration_providers['profile-a']
                    async def expression(brief, guard):
                        return await realize_session_narration(hass,narration=brief,admission=guard,
                            fallback_text=brief.seed,conf=runtime.config,debug=debug)
                    manager.connect_narration('profile-a',active.session_id,expression,registration[2],
                        capture_authority=registration[3],archive_admission=registration[4])
                    await manager.async_update_playback_projection(owner_profile_id='profile-a',session_id=active.session_id,
                        state='playing',media_identity=catalog['uri'],title=catalog['title'],artist=catalog['artist'],
                        duration_ms=600000,position_ms=0)
                    async def insight():
                        return {'_qualified_facts':(fact,)}
                    moment = await manager.async_process_track_started(owner_profile_id='profile-a',session_id=active.session_id,
                        insight_provider=insight,media_identity=catalog['uri'],require_current_playback=True,allow_initial_facts=True)
                    active = manager.current_active('profile-a')
                    text = moment.content if moment else None
                    if moment:
                        assert moment.moment_type.value == 'album'
                        assert moment in active.broadcast.state.dj_moments
                    await manager.async_end(owner_profile_id='profile-a',session_id=active.session_id)
                    page = await query_service(hass,runtime.ask_dj_history).async_timeline_page('profile-a',active.session_id)
                    saved = [e for e in page['entries'] if moment and e.get('moment_id') == moment.moment_id]
                    assert not moment or (len(saved) == 1 and saved[0]['text'] == text)
                    rows.append({'id':case,'persona':persona,'mood':mood,'language':'nl',
                        'status':'PASS' if moment else 'FAIL','actually_published_text':text,
                        'reopened_text':saved[0]['text'] if saved else None,'debug':debug,
                        'sources':moment.as_dict().get('sources',[]) if moment else [],
                        'model_attempts':len(model_receipts)-before,
                        'playback_boundary':'SYNTHETIC','editorial':'PENDING'})
                finally:
                    ACTIVE_CASE.reset(token)
                    if manager.current_active('profile-a') is not None:
                        await manager.async_end(owner_profile_id='profile-a',session_id=active.session_id)
                    Path('/lab/album-partial.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    return {'scope':'FIXED_EIGHT_DUTCH_ALBUM_PERSONA_MOOD_ONE_REAL_PUBLIC_CORPUS_AND_HA_EXPRESSION',
        'cases':rows, 'status':'PASS' if len(rows)==8 and all(r['status']=='PASS' for r in rows) else 'FAIL',
        'public_evidence_sha256':package_hash,'actual_source_requests':source_requests,
        'maximum_paid_attempts':16,'editorial':'PENDING','native':'NOT_RUN','audible':'NOT_RUN'}


async def run_openings(hass, runtime, manager, call, model_receipts):
    """Eight fixed actual paired starts; real prose, synthetic household/output.

    This is a bounded first-draft sample, not the complete language/style matrix.
    Store the exact published and reopened text, including an honest fallback.
    """
    from datetime import UTC, datetime
    from uuid import UUID
    from pathlib import Path
    from custom_components.djconnect.domain.profile.dj_settings import DJSettings
    from custom_components.djconnect.session_conversation import query_service
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository

    personas = ('home_dj', 'radio_dj', 'club_dj', 'festival_dj')
    rows = []
    repository = manager._settings_repository
    if repository is None:
        # The older diagnostic fixture predates Profile settings. Reuse the
        # actual production settings owner in this fresh isolated household.
        repository = ProfileDJSettingsRepository(persistence_service(hass))
        manager._settings_repository = repository
    for index, (persona, mood) in enumerate((p, m) for p in personas for m in ('chill', 'party')):
        # Hold language and Presence fixed for a real within-Persona Mood
        # comparison. Structural five-language/four-Presence coverage is separate.
        locale, presence = 'nl', 'balanced'
        case = 'opening-'+persona+'-'+mood+'-'+locale+'-'+presence
        now = int(datetime.now(UTC).timestamp()*1000)
        op = str(UUID(int=(now << 80) | (7 << 76) | (2 << 62) | (index+1)))
        defaults = await repository.async_read('profile-a', authorize=lambda: True)
        await repository.async_accept_user_choice('profile-a', operation_id=op, binding='a'*64,
            patch=DJSettings(persona=persona, mood=mood, presence=presence).as_dict(),
            expected_defaults_revision=defaults['defaults_revision'], now_ms=now, authorize=lambda: True)
        before = len(model_receipts)
        began = asyncio.get_running_loop().time()
        active = None
        try:
            result = await call('session/start', {'language':locale}, label=case, expected=201)
            active = manager.current_active('profile-a')
            assert active and active.session_id == result['session']['session_id']
            await playback_observation_manager(hass).async_stop('profile-a', active.session_id)
            moment = next(m for m in active.broadcast.state.dj_moments
                          if dict(m.generation_metadata).get('purpose') == 'session_opening')
            assert (active.selected_mood, active.dj_persona.value, active.selected_presence) == (mood, persona, presence)
            assert active.broadcast.state.dj_moments[0] is moment
            assert await manager.async_open_session(owner_profile_id='profile-a', session_id=active.session_id) is moment
            assert not moment.actions
            await call('session/end', {'session_id':active.session_id}, label=case+'-end', expected=200)
            page = await query_service(hass, runtime.ask_dj_history).async_timeline_page('profile-a', active.session_id)
            saved = [e for e in page['entries'] if e.get('moment_id') == moment.moment_id]
            assert len(saved) == 1 and saved[0]['text'] == moment.content
            attempts = len(model_receipts)-before
            assert attempts <= 2
            generated = dict(moment.generation_metadata).get('realization') == 'qualified_runtime_narration_v1'
            rows.append({'id':case, 'language':locale, 'persona':persona, 'mood':mood, 'presence':presence,
                'status':'PASS' if generated else 'FAIL', 'generated':generated,
                'actually_published_text':moment.content, 'reopened_text':saved[0]['text'],
                'model_attempts':attempts, 'seconds':round(asyncio.get_running_loop().time()-began, 3),
                'native':'NOT_RUN', 'audible':'NOT_RUN', 'editorial':'PENDING'})
        finally:
            current = manager.current_active('profile-a')
            if current is not None:
                await playback_observation_manager(hass).async_stop('profile-a', current.session_id)
                await manager.async_end(owner_profile_id='profile-a', session_id=current.session_id)
            Path('/lab/opening-partial.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    return {'scope':'FIXED_EIGHT_DUTCH_PERSONA_MOOD_PAIRED_OPENINGS_BALANCED_NOT_FULL_QUALITY_MATRIX',
            'status':'PASS' if all(r['generated'] for r in rows) else 'FAIL', 'cases':rows,
            'maximum_paid_attempts':16, 'native':'NOT_RUN', 'audible':'NOT_RUN', 'editorial':'PENDING'}


async def run(hass, runtime, manager, active):
    if os.environ.get('DJC_RESEARCHED_PRODUCER') == '1':
        return await run_researched_producer(hass, runtime, manager, active)
    if os.environ.get('DJC_RESEARCHED_ARTIST') == '1':
        return await run_researched_artist(hass, runtime, manager, active)
    from custom_components.djconnect.pipeline import realize_session_narration
    from custom_components.djconnect.narration_brief import qualify
    from custom_components.djconnect.moment_expression import realize
    from custom_components.djconnect.session_facts import catalog_facts
    from scripts.verification.askdj_contextual_golden import ACTIVE_CASE
    from tests.context_variation_fixtures import source

    # External source boundary fixture reproduces the reported edition sentence.
    # These values MUST remain local; the request observer checks both model calls.
    fact = catalog_facts({
        'uri':'spotify:track:'+'1'*22,'title':'Synthetic recording',
        'artist':'Synthetic artist','album_name':'Wednesday Morning, 3 A.M.',
        'album_uri':'spotify:album:'+'2'*22,
        'release_date':'1964-10-19','release_date_precision':'day'})[0]
    personas=('home_dj','radio_dj','club_dj','festival_dj')
    moods=('chill','groove','energy','party')
    families=('description','formation','birth','edition')
    cells=[(p,m,'nl',families[(pi+mi)%4]) for pi,p in enumerate(personas) for mi,m in enumerate(moods)]
    cells.extend(('home_dj','energy',lang,'description') for lang in ('en','de','fr','es'))
    semaphore=asyncio.Semaphore(2)
    authority=manager._narration_providers[active.owner_profile_id][2]

    def guard():
        authority()
        if manager.current_active(active.owner_profile_id) is not active:
            raise PermissionError('probe_session_changed')

    async def one(persona,mood,locale,family):
        async with semaphore:
            identifier='narration-'+family+'-'+persona+'-'+mood+'-'+locale
            token=ACTIVE_CASE.set(identifier)
            try:
                selected=source(family,0)[1] if family != 'edition' else fact
                seed=realize(selected,locale=locale,persona=persona,mood=mood,form=0)[1]
                brief=qualify(selected,locale=locale,persona=persona,mood=mood,seed=seed)
                debug={}
                began=asyncio.get_running_loop().time()
                text=await realize_session_narration(hass,fallback_text=seed,
                    conf=runtime.config,narration=brief,admission=guard,debug=debug)
                return {'id':identifier,'persona':persona,'mood':mood,'language':locale,'family':family,
                    'status':'PASS' if not debug.get('fallback_used',True) and text!=seed else 'FAIL',
                    'before':seed,'after':str(text),'frame':getattr(text,'frame',None),
                    'debug':debug,'seconds':round(asyncio.get_running_loop().time()-began,3)}
            finally:
                ACTIVE_CASE.reset(token)

    rows=await asyncio.gather(*(one(*cell) for cell in cells))
    # String inequality is just a prerequisite; human editorial review remains required.
    return {'scope':'PAID_HA_EXPRESSION_PILOT_20_CELLS_NOT_FULL_RELEASE_MATRIX',
            'cases':rows,'status':'PASS' if all(row['status']=='PASS' for row in rows) else 'FAIL',
            'missing_full_80_cell_all_family_editorial_qualification':True}


async def run_researched_artist(hass, runtime, manager, active):
    """Same actual public corpus, eight first drafts, no installed/publication claim.

    Real Wikipedia/WD/MB retrieval establishes the public identity. Pin its
    retrieved evidence once for the comparison; each expression still uses the
    real configured HA model route and the production admission/assessment.
    """
    from dataclasses import replace
    import hashlib
    import re
    from urllib.parse import urlencode
    from unittest.mock import patch
    from custom_components.djconnect.ask_dj import public_research as research
    from custom_components.djconnect.session_facts import artist_facts, match_name, MBID
    from custom_components.djconnect.narration_brief import qualify
    from custom_components.djconnect.pipeline import realize_session_narration
    from scripts.verification.askdj_contextual_golden import ACTIVE_CASE

    authority = manager._narration_providers[active.owner_profile_id][2]
    def admission():
        authority()
        if manager.current_active(active.owner_profile_id) is not active:
            raise PermissionError('probe_session_changed')
    async def guard():
        admission()

    async with research.PublicFetch(guard) as fetch:
        page = await research.wikipedia(fetch, 'Son Mieux', 'Introduce this music group', 'nl', expected_roles=('Group',))
        assert page and page.entity_id and page.revision_url, 'public_artist_identity_unavailable'
        status, body, _ = await fetch.request('https://www.wikidata.org/w/api.php?'+urlencode({
            'action':'wbgetentities','ids':page.entity_id,'props':'claims','format':'json'}))
        assert status == 200
        entity = json.loads(body)['entities'][page.entity_id]
        ids = {c.get('mainsnak',{}).get('datavalue',{}).get('value')
            for c in entity.get('claims',{}).get('P434',[]) if c.get('rank') != 'deprecated'}
        assert len(ids) == 1 and MBID.fullmatch(next(iter(ids))), 'reciprocal_artist_identity_unavailable'
        mbid = next(iter(ids))
        status, body, _ = await fetch.request('https://musicbrainz.org/ws/2/artist/'+mbid+'?fmt=json&inc=url-rels')
        assert status == 200
        person = json.loads(body)
        bound = {m[1] for r in person.get('relations',[]) if r.get('type') == 'wikidata'
            and (m:=re.fullmatch(r'https?://www.wikidata.org/wiki/(Q[1-9][0-9]*)',r.get('url',{}).get('resource','')))}
        assert person.get('id') == mbid and match_name(person.get('name')) == match_name('Son Mieux')
        assert bound == {page.entity_id}, 'reciprocal_artist_identity_mismatch'
    sources, state = await research.research('Son Mieux','Introduce this music group','nl',guard,
        qualified_music=True,expected_roles=('Group',),expected_entity_id=page.entity_id,allow_web=False,
        original_paragraphs=True)
    assert sources and all(s.entity_id == page.entity_id for s in sources)
    # Synthetic playback boundary; public source facts themselves were fetched.
    catalog = {'uri':'spotify:track:'+'R'*22,'artist':person['name']}
    fact = replace(artist_facts(catalog,person)[0],public_artist_qid=page.entity_id)
    package = {'original_cc0':fact.copy_for('nl')[1], 'original_url':fact.source_url,
        'wikidata_id':page.entity_id, 'sources':[s.model_data() for s in sources]}
    package_hash = hashlib.sha256(json.dumps(package,sort_keys=True).encode()).hexdigest()
    async def pinned(subject, question, locale, owned_guard, **kwargs):
        await owned_guard()
        assert subject == person['name'] and kwargs['expected_entity_id'] == page.entity_id
        assert kwargs['allow_web'] is False
        return list(sources), state

    rows = []
    with patch.object(research,'research',pinned):
        for persona in ('home_dj','radio_dj','club_dj','festival_dj'):
            for mood in ('chill','party'):
                identifier = 'public-artist-'+persona+'-'+mood+'-nl'
                token = ACTIVE_CASE.set(identifier)
                try:
                    seed = fact.copy_for('nl')[1]
                    brief = qualify(fact,locale='nl',persona=persona,mood=mood,seed=seed)
                    debug = {}
                    text = await realize_session_narration(hass,narration=brief,admission=admission,
                        fallback_text=seed,conf=runtime.config,debug=debug)
                    accepted = getattr(text,'accepted',None)
                    rows.append({'id':identifier,'persona':persona,'mood':mood,'language':'nl',
                        'before':seed,'after':str(text),'status':'PASS' if accepted is not None else 'FAIL',
                        'debug':debug,'same_public_corpus_sha256':package_hash,
                        'sources':accepted.sources() if accepted else [],'editorial_acceptance':'NOT_RUN',
                        'actual_published':'NOT_RUN_EXPRESSION_PILOT_ONLY'})
                finally:
                    ACTIVE_CASE.reset(token)
    return {'scope':'PAID_HA_RESEARCHED_ARTIST_EXPRESSION_8_CELLS_NOT_PUBLICATION_OR_RELEASE',
        'cases':rows,'public_evidence_package':package,'public_evidence_sha256':package_hash,
        'status':'PASS' if all(row['status']=='PASS' for row in rows) else 'FAIL',
        'editorial_acceptance':'NOT_RUN','all_family_qualification':'NOT_RUN'}


async def run_researched_producer(hass, runtime, manager, active):
    """Two real expressions over the reported credit pair's public recording.

    Fresh source identity is genuinely retrieved, then pinned for comparison.
    Playback remains a synthetic lab binding; no story is published or installed.
    """
    from dataclasses import asdict
    import hashlib
    from unittest.mock import patch
    from custom_components.djconnect.ask_dj import public_research as research
    from custom_components.djconnect import public_artist_narration as narration
    from custom_components.djconnect.session_facts import recording_facts, match_name
    from custom_components.djconnect.narration_brief import qualify
    from custom_components.djconnect.pipeline import realize_session_narration
    from scripts.verification.askdj_contextual_golden import ACTIVE_CASE

    authority = manager._narration_providers[active.owner_profile_id][2]
    def admission():
        authority()
        if manager.current_active(active.owner_profile_id) is not active:
            raise PermissionError('probe_session_changed')
    async def guard():
        admission()
    recording_id = '852ee1bd-5d68-4421-8375-68ac317bffb3'
    async with research.PublicFetch(guard) as fetch:
        status, body, _ = await fetch.request('https://musicbrainz.org/ws/2/recording/'+recording_id
            +'?fmt=json&inc=artist-rels+artist-credits')
        if status != 200:
            error = RuntimeError('producer_recording_source_unavailable')
            error.public_http_status = status
            raise error
        recording = json.loads(body)
        artist = ', '.join(c.get('artist',{}).get('name','') for c in recording.get('artist-credit',[])
            if isinstance(c,dict))
        assert recording.get('id') == recording_id and match_name(artist) == match_name('Editors')
        catalog = {'uri':'spotify:track:'+'P'*22,'title':recording['title'],'artist':artist}
        fact = recording_facts(catalog,recording)[0]
        credit = narration.producer_subject(fact)
        assert credit is not None, 'recording_roles_not_qualified'
        identity = await narration.producer_identity(fetch,credit)
        assert identity is not None, 'reciprocal_producer_identity_unavailable'
        sources,state = await research.research(credit.name,'Introduce the credited producer through a documented activity',
            'nl',guard,qualified_music=True,expected_roles=(identity[3],),expected_entity_id=identity[4],
            allow_web=False,fetch=fetch,original_paragraphs=True)
        assert sources, 'producer_public_references_unavailable'
        source_requests = fetch.requests
    package = {'normalized_fact':asdict(fact),'selected_contributor':identity,
        'sources':[s.model_data() for s in sources],'actual_source_requests':source_requests,
        'synthetic_playback_boundary':True}
    package_hash = hashlib.sha256(json.dumps(package,sort_keys=True).encode()).hexdigest()
    async def pinned(subject,question,locale,owned_guard,**kwargs):
        await owned_guard()
        assert subject == credit.name and kwargs['expected_entity_id'] == identity[4]
        assert kwargs['allow_web'] is False
        return list(sources),state
    async def pinned_identity(fetch,selected):
        await fetch.guard()
        assert selected == credit
        return identity
    rows=[]
    with patch.object(research,'research',pinned), patch.object(narration,'producer_identity',pinned_identity):
        for mood in ('chill','party'):
            identifier='public-producer-home_dj-'+mood+'-nl'
            token=ACTIVE_CASE.set(identifier)
            try:
                seed=fact.copy_for('nl')[1]
                brief=qualify(fact,locale='nl',persona='home_dj',mood=mood,seed=seed)
                debug={}
                text=await realize_session_narration(hass,narration=brief,admission=admission,
                    fallback_text=seed,conf=runtime.config,debug=debug)
                accepted=getattr(text,'accepted',None)
                rows.append({'id':identifier,'persona':'home_dj','mood':mood,'language':'nl',
                    'before':seed,'after':str(text),'status':'PASS' if accepted else 'FAIL',
                    'debug':debug,'same_public_corpus_sha256':package_hash,
                    'sources':accepted.sources() if accepted else [],'editorial_acceptance':'NOT_RUN',
                    'actual_published':'NOT_RUN_EXPRESSION_PILOT_ONLY'})
            finally:
                ACTIVE_CASE.reset(token)
    return {'scope':'PAID_HA_RESEARCHED_PRODUCER_EXPRESSION_2_CELLS_NOT_PUBLICATION_OR_RELEASE',
        'cases':rows,'public_evidence_package':package,'public_evidence_sha256':package_hash,
        'status':'PASS' if all(row['status']=='PASS' for row in rows) else 'FAIL',
        'editorial_acceptance':'NOT_RUN','all_family_qualification':'NOT_RUN'}
