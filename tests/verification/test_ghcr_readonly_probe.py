import json
import unittest
from tools.verification.ghcr_readonly_probe import probe

class GHCRReadProbeTest(unittest.TestCase):
    def call(self, replies):
        calls=[]
        def request(url, auth):
            calls.append((url, auth))
            return replies.pop(0)
        result=probe('actor','PRIVATE_CANARY',request)
        self.assertNotIn('PRIVATE_CANARY', json.dumps(result))
        self.assertTrue(all(url.startswith('https://ghcr.io/') for url,_ in calls))
        return result,calls
    def test_visible_only_reports_count(self):
        result,calls=self.call([(200,b'{"token":"SECRET_TOKEN"}'),(200,b'{"tags":["latest","1.1","private-value"]}')])
        self.assertEqual(result,{'registry_read':'VISIBLE','selected_tags_visible_first_page':2,'write_permission':'NOT_TESTED','absence':'NOT_ASSERTED'})
        self.assertEqual(len(calls),2)
    def test_failure_or_invisible_never_asserts_absence(self):
        for code in (401,403,404,500):
            with self.subTest(code=code):
                result,_=self.call([(200,b'{"token":"SECRET_TOKEN"}'),(code,b'PRIVATE_CANARY')])
                self.assertEqual(result['registry_read'],'UNKNOWN')
                self.assertEqual(result['absence'],'NOT_ASSERTED')
    def test_bad_payload_and_token(self):
        for payload in (b'{',b'{"tags":null}',b'{"tags":[42]}'):
            result,_=self.call([(200,b'{"token":"SECRET_TOKEN"}'),(200,payload)])
            self.assertEqual(result['registry_read'],'UNKNOWN')
        result,calls=self.call([(200,b'{"token":"bad\\nsecret"}')])
        self.assertEqual(result['registry_read'],'UNKNOWN')
        self.assertEqual(len(calls),1)
