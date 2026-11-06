"""Provider grant evidence is neither requested permissions nor credential custody."""
import importlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from tests.test_spotify_oauth import install_oauth_stubs


class ScopeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_oauth_stubs()
        cls.oauth=importlib.import_module('custom_components.djconnect.spotify_oauth')

    def evidence(self,token,**kw):
        return self.oauth.spotify_scope_evidence(token,requested='user-modify-playback-state playlist-read-private',
            client_id='public-client',source='authorization_code',observed_at='2026-11-06T12:00:00+00:00',**kw)

    def test_actual_partial_grant_never_inherits_requested_permissions(self):
        record=self.evidence({'scope':'playlist-read-private','access_token':'DO_NOT_STORE','refresh_token':'DO_NOT_STORE'})
        status=self.oauth.spotify_scope_status({'spotify_client_id':'public-client','spotify_scopes':'user-modify-playback-state playlist-read-private','spotify_scope_evidence':record})
        self.assertEqual(status['granted_scopes'],['playlist-read-private'])
        self.assertIn('user-modify-playback-state',status['missing_granted_scopes'])
        self.assertNotIn('DO_NOT_STORE',json.dumps(record))

    def test_missing_or_malformed_scope_is_unknown_without_requested_fallback(self):
        for token in ({},{'scope':None},{'scope':['user-modify-playback-state']},
                      {'scope':'access_token=DO_NOT_STORE'},{'scope':'x'*4097}):
            record=self.evidence(token)
            self.assertEqual(record['status'],'unknown')
            self.assertIsNone(record['granted_scopes'])
            self.assertNotIn('DO_NOT_STORE',json.dumps(record))

    def test_empty_explicit_scope_is_known_empty_not_a_full_grant(self):
        record=self.evidence({'scope':''})
        self.assertEqual(record['status'],'known')
        self.assertEqual(record['granted_scopes'],[])

    def test_new_authorization_without_scope_cannot_keep_old_grant(self):
        original=self.evidence({'scope':'playlist-read-private'})
        unknown=self.evidence({},previous=original)
        self.assertEqual(unknown['status'],'unknown')

    def test_same_client_refresh_without_scope_preserves_original_receipt_time(self):
        original=self.evidence({'scope':'playlist-read-private'})
        new=self.oauth.spotify_scope_evidence({},requested='different-request',client_id='public-client',
            source='refresh_token',previous=original,observed_at='2026-11-06T13:00:00+00:00')
        self.assertEqual(new,original)

    def test_changed_client_refresh_cannot_inherit_receipt(self):
        original=self.evidence({'scope':'playlist-read-private'})
        new=self.oauth.spotify_scope_evidence({},requested='playlist-read-private',client_id='other-client',
            source='refresh_token',previous=original)
        self.assertEqual(new['status'],'unknown')

    def test_current_provider_scope_supersedes_old_refresh_evidence(self):
        original=self.evidence({'scope':'playlist-read-private'})
        new=self.oauth.spotify_scope_evidence({'scope':'user-modify-playback-state'},requested='',
            client_id='public-client',source='refresh_token',previous=original)
        self.assertEqual(new['granted_scopes'],['user-modify-playback-state'])

    def test_legacy_requested_scopes_remain_separate_from_unknown_grant(self):
        status=self.oauth.spotify_scope_status({'spotify_client_id':'public-client','spotify_scopes':'playlist-read-private'})
        self.assertEqual(status['requested_scopes'],['playlist-read-private'])
        self.assertIsNone(status['granted_scopes'])
        self.assertIsNone(status['missing_granted_scopes'])

    def test_forged_or_wrong_client_evidence_is_not_reported_as_actual(self):
        original=self.evidence({'scope':'playlist-read-private'})
        for conf in ({'spotify_client_id':'other-client','spotify_scope_evidence':original},
                     {'spotify_client_id':'public-client','spotify_scope_evidence':{**original,'access_token':'DO_NOT_STORE'}}):
            status=self.oauth.spotify_scope_status(conf)
            self.assertIsNone(status['granted_scopes'])
            self.assertNotIn('DO_NOT_STORE',json.dumps(status))

    def test_storage_only_updates_current_owner_and_never_credentials(self):
        entry=SimpleNamespace(entry_id='owner',data={'spotify_client_id':'public-client','spotify_scopes':'playlist-read-private','spotify_refresh_token':'PRIVATE'})
        update=Mock()
        entries=SimpleNamespace(async_get_entry=lambda _:entry,async_update_entry=update)
        hass=SimpleNamespace(config_entries=entries)
        self.oauth.store_spotify_scope_evidence(hass,entry,{'scope':'playlist-read-private','access_token':'DO_NOT_STORE'},client_id='public-client')
        new=update.call_args.kwargs['data']
        self.assertEqual(new['spotify_refresh_token'],'PRIVATE')
        self.assertNotIn('DO_NOT_STORE',json.dumps(new))
        self.assertEqual(entry.data.get('spotify_scope_evidence'),None)
        update.reset_mock()
        entries.async_get_entry=lambda _:None
        self.oauth.store_spotify_scope_evidence(hass,entry,{'scope':'playlist-read-private'},client_id='public-client')
        update.assert_not_called()
