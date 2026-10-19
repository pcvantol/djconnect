"""Evidence/permission boundaries with explicit model fixtures, not real quality."""
from copy import deepcopy
import json
import unittest

from tools.verification import askdj_catalogue_variations as variants
from tests import test_ask_dj_catalogue_golden as base_fixture


class VariationTests(unittest.IsolatedAsyncioTestCase):
    def base(self):
        return base_fixture.CatalogueGoldenTest().receipt_fixture()

    async def fixture_call(self, prompt, language, purpose):
        data = json.loads(prompt.split('\nData:\n', 1)[1])
        if purpose == 'variation_generation':
            return json.dumps({'language':language, 'variants':[
                {'id':r['id'],'kind':r['kind'],'text':'Fixture '+r['question']}
                for r in data['questions']]})
        return json.dumps({'language':language,'proposal_sha256':data['proposal_sha256'],'checks':[
            {'id':r['id'],'same_intent':True,'same_reference':True,
             'same_permission':True,'language_ok':True} for r in data['originals']]})

    async def test_failed_partial_stale_or_selected_base_spends_zero_generation_calls(self):
        original = self.base()
        fixtures = []
        for mutate in (lambda r:r.update(status='FAIL'),
                       lambda r:r['cases'].pop(),
                       lambda r:r.update(selected_case_ids=['catalogue-play.artist-nl']),
                       lambda r:r.update(source_unchanged=False),
                       lambda r:r.update(manifest_sha256='stale'),
                       lambda r:r.update(source_hashes={'other':'candidate'})):
            fixture = deepcopy(original)
            mutate(fixture)
            fixtures.append(fixture)
        calls = []
        async def forbidden(*args):
            calls.append(args)
            raise AssertionError('no model callback allowed before full base gate')
        for fixture in fixtures:
            with self.assertRaises(ValueError):
                await variants.generate(fixture,source_hashes=original['source_hashes'],ask=forbidden)
        self.assertEqual(calls,[])

    async def test_frozen_inputs_reuse_all_independent_oracles_and_full_context_chains(self):
        raw = self.base()
        corpus = await variants.generate(raw,source_hashes=raw['source_hashes'],ask=self.fixture_call)
        self.assertFalse(corpus['product_qualified'])
        self.assertEqual(corpus['status'],'PENDING_ACTUAL_EXECUTION')
        self.assertEqual(corpus['attempts'],variants.MAX_ATTEMPTS)
        actual = variants.cases(corpus)
        base = variants.base.cases()+variants.base.chain_cases()
        self.assertEqual(len(actual),len(base))
        for original, case in zip(base,actual,strict=True):
            self.assertEqual(case['expected'],original['expected'])
            self.assertEqual(case['language'],original['language'])
            self.assertNotEqual(case['question'],original['question'])
            self.assertNotEqual(case['id'],original['id'])
            self.assertEqual(case['variant_of'],original['id'])
        by_id = {c['id']:c for c in actual}
        for case in actual:
            if case.get('operation')=='duplicate':
                self.assertEqual(case['question'],by_id[case['chain']+'-accept']['question'])
                self.assertEqual(case['expected']['effect'],'none')

    async def test_permission_change_or_uncertain_semantics_aborts_without_retry_or_partial_corpus(self):
        raw = self.base()
        for field, value in (('same_permission',False),('same_reference',False),
                             ('same_intent','true'),('language_ok',False)):
            calls=[]
            async def altered(prompt,language,purpose):
                calls.append(purpose)
                response=await self.fixture_call(prompt,language,purpose)
                if purpose=='variation_meaning_review':
                    body=json.loads(response)
                    body['checks'][0][field]=value
                    return json.dumps(body)
                return response
            with self.assertRaises(ValueError):
                await variants.generate(raw,source_hashes=raw['source_hashes'],ask=altered)
            self.assertEqual(calls,['variation_generation','variation_meaning_review'])

    async def test_variant_execution_uses_its_frozen_questions_and_cannot_replace_base_evidence(self):
        raw=self.base()
        corpus=await variants.generate(raw,source_hashes=raw['source_hashes'],ask=self.fixture_call)
        original=deepcopy(raw)
        compiled=variants.cases(corpus)
        mapping={c['variant_of']:c for c in compiled}
        for row in raw['cases']:
            case=mapping[row['id']]
            row['id']=case['id']
            row['question_sha256']=variants.hashlib.sha256(case['question'].encode()).hexdigest()
        for receipt in raw['core_transports']:
            case=mapping[receipt['case']]
            receipt['case']=case['id']
            receipt['request']['text']=case['question']
            receipt['request']['client_message_id']=(case['chain']+'-accept'
                if case.get('operation')=='duplicate' else case['id'])
        for call in raw['model_calls']:
            call['case_id']=mapping[call['case_id']]['id']
        raw.update(qualification='REAL_PAIRED_HA_CATALOGUE_VARIATIONS_V1',
                   manifest_sha256=variants.base.variation_manifest(corpus))
        self.assertTrue(variants.base.validate_variation_report(raw,corpus=corpus,source_hashes=raw['source_hashes']))
        self.assertFalse(variants.base.validate_report(raw,source_hashes=raw['source_hashes']))
        self.assertFalse(variants.base.validate_variation_report(original,corpus=corpus,source_hashes=raw['source_hashes']))
        raw['core_transports'][0]['request']['text']=mapping[next(iter(mapping))]['variant_of']
        self.assertFalse(variants.base.validate_variation_report(raw,corpus=corpus,source_hashes=raw['source_hashes']))

    async def test_changed_corpus_languages_ids_text_or_catalogue_pin_cannot_silently_enter_golden(self):
        raw = self.base()
        corpus=await variants.generate(raw,source_hashes=raw['source_hashes'],ask=self.fixture_call)
        for mutate in (lambda c:c.update(seed_sha256='stale'),
                       lambda c:c['batches'].pop(),
                       lambda c:c['batches'][0]['variants'][0].update(id='foreign'),
                       lambda c:c['batches'][0]['variants'][0].update(text='https://example.org'),
                       lambda c:c['batches'][0]['variants'][0].update(text=variants.seeds()[0]['question']),
                       lambda c:c['batches'][0]['variants'][0].update(expected={'effect':'none'}),
                       lambda c:c['batches'][0]['variants'][0].update(text='Another apparently valid sentence'),
                       lambda c:c['batches'][0].update(reviewed_proposal_sha256='stale'),
                       lambda c:c['batches'][0]['checks'][0].update(same_permission=False)):
            changed=deepcopy(corpus)
            mutate(changed)
            with self.assertRaises(ValueError):
                variants.cases(changed)

    def test_duplicate_json_keys_and_changed_artist_name_are_rejected(self):
        with self.assertRaises(ValueError):
            variants._object('{"language":"en","language":"nl"}')
        rows=[r for r in variants.seeds() if r['language']=='en']
        value={'language':'en','variants':[
            {'id':r['id'],'kind':r['kind'],'text':'Fixture '+r['question']} for r in rows]}
        value['variants'][0]['text']=value['variants'][0]['text'].replace(variants.base.ARTIST,'Another band')
        with self.assertRaises(ValueError):
            variants._variants(json.dumps(value),'en',rows)

    def test_release_requires_frozen_variations_after_the_exact_base_profile(self):
        from tools.verification import run_askdj_release_matrix as release
        profiles=list(release.PROFILES)
        self.assertLess(profiles.index('catalogue_golden'),profiles.index('catalogue_variations'))
        self.assertEqual(release.PROFILES['catalogue_variations'][0],'catalogue-variations-golden.json')
        self.assertNotEqual(release.PROFILES['catalogue_golden'][0],release.PROFILES['catalogue_variations'][0])
