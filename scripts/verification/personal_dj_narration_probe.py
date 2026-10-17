"""Paid expression pilot on the existing isolated real HA agent, not a release GO."""
import asyncio
import json


async def run(hass, runtime, manager, active):
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
