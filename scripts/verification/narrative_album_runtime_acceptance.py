"""Own bounded lab: fixture only external Spotify HTTP, real producer chain."""
from __future__ import annotations
import asyncio
import json
import hashlib
import os
from pathlib import Path
import ssl
import time
from unittest.mock import patch

from aiohttp import web
from custom_components.djconnect.spotify_backend import SpotifyBackend
from custom_components.djconnect.playback_observation import playback_observation_manager
from custom_components.djconnect.session_runtime import DJPersona
from custom_components.djconnect import session_facts
from custom_components.djconnect.session_facts import SessionFactsResolver
from custom_components.djconnect.paired_live_contract import PAIRED_LIVE_PATH

AlbumContinuityFact = getattr(session_facts, "AlbumContinuityFact", ())


class AlbumLab:
    def __init__(self, hass, manager, clock, integration):
        self.hass, self.manager, self.clock, self.integration = hass, manager, clock, integration
        self.observer = playback_observation_manager(hass)
        self.raw = {}
        self.calls = 0
        self.source_patch = None
        self.owner = {}

    async def provider(self, backend, method, path, **kwargs):
        self.calls += 1
        assert method == "GET"
        if path == "/me/player":
            return self.raw
        if path == "/me/player/queue":
            return {"currently_playing": self.raw.get("item"), "queue": []}
        raise AssertionError("Unexpected provider route: " + path)

    def begin(self):
        if self.source_patch is None:
            lab = self
            async def external(backend, method, path, **kwargs):
                return await lab.provider(backend, method, path, **kwargs)
            self.source_patch = patch.object(SpotifyBackend, "_request", external)
            self.source_patch.start()

    def raw_track(self, number, *, album="Z"*22, name="Exact edition",
                  date="2001-03-04", precision="day", playing=True, isrc=""):
        ident = f"{number:022d}"
        return {"is_playing": playing, "progress_ms": 0,
                "device": {"id": "fixture-output", "name": "Own lab"},
                "item": {"type": "track", "id": ident, "uri": "spotify:track:"+ident,
                         "name": f"Observed track {number}", "duration_ms": 300000, "external_ids":{"isrc":isrc},
                         "artists": [{"id": "X"*22, "name": "Catalog artist"}],
                         "album": {"id": album, "uri": "spotify:album:"+album,
                                   "name": name, "release_date": date,
                                   "release_date_precision": precision, "images": []}}}

    async def start(self, *, mode="balanced", locale="nl", persona=DJPersona.HOME_DJ, direct_persona=False):
        self.begin()
        active=await self.manager.async_get_active("profile-a")
        if active:
            response=await self.owner["client"].post("/api/djconnect/v1/session/end",
                headers=self.owner["headers"],json={**self.owner["identity"],"session_id":active.session_id})
            assert response.status==200, await response.json()
        self.raw={}
        response=await self.owner["client"].post("/api/djconnect/v1/session/start",
            headers=self.owner["headers"],json={**self.owner["identity"],
            "mood":"groove","dj_persona":(persona if direct_persona or persona is not DJPersona.FESTIVAL_DJ else DJPersona.HOME_DJ).value,"language":locale,
            "session_start_strategy":"discover"})
        reply=await response.json()
        assert response.status==201, reply
        session=await self.manager.async_get_active("profile-a")
        if persona is DJPersona.FESTIVAL_DJ and not direct_persona:
            session=await self.manager.async_update_persona(owner_profile_id="profile-a",
                session_id=session.session_id,dj_persona=persona)
        if mode != session.selected_presence:
            await self.presence(mode)
        return await self.manager.async_get_active("profile-a")

    async def presence(self, value):
        active = await self.manager.async_get_active("profile-a")
        response = await self.owner["client"].post("/api/djconnect/v1/session/presence",
            headers=self.owner["headers"], json={**self.owner["identity"], "contract_version":1,
            "session_id":active.session_id, "selected_presence":value,
            "expected_presence_revision":active.presence_revision})
        assert response.status == 200
        return await response.json()

    async def step(self, number, **changes):
        self.clock.advance(200)
        self.raw = self.raw_track(number, **changes)
        active = await self.manager.async_get_active("profile-a")
        before = len(active.broadcast.state.dj_moments)
        if "profile-a" not in self.observer._spotify_sessions:
            async def no_interpretation():
                return {}
            await self.observer.async_start_spotify(integration_runtime=self.integration,
                session=active, insight_provider=no_interpretation)
        else:
            await self.observer._async_poll_spotify(self.observer._spotify_sessions["profile-a"])
        active = await self.manager.async_get_active("profile-a")
        moments = active.broadcast.state.dj_moments[before:]
        return moments[-1] if moments else None

    async def owner_snapshot(self):
        active = await self.manager.async_get_active("profile-a")
        response = await self.owner["client"].get("/api/djconnect/v1/session/broadcast/"+active.session_id,
            headers=self.owner["headers"], params=self.owner["identity"])
        assert response.status == 200
        return (await response.json())["snapshot"]

    async def live(self):
        active = await self.manager.async_get_active("profile-a")
        ws = await self.owner["client"].ws_connect(PAIRED_LIVE_PATH)
        assert (await ws.receive_json())["type"] == "auth_required"
        token = self.owner["headers"]["Authorization"].removeprefix("Bearer ")
        await ws.send_json({"type":"auth", "protocol_version":1,
                           **self.owner["identity"], "device_token":token})
        assert (await ws.receive_json())["type"] == "auth_ok"
        await ws.send_json({"id":1,"type":"djconnect/session/broadcast/subscribe",
                           "session_id":active.session_id})
        response = await ws.receive_json()
        assert response["success"], response
        return ws, response["result"]

    async def qualify(self, client, identity, headers):
        self.owner = {"client":client, "identity":identity, "headers":headers}
        input_hashes={str(number):hashlib.sha256(json.dumps(self.raw_track(number),
                      sort_keys=True,separators=(",",":")).encode()).hexdigest() for number in (1,2)}
        if os.environ.get("DJC_NARRATIVE_BASELINE")=="1":
            session=await self.start()
            a=await self.step(1)
            b=await self.step(2)
            assert a and a.moment_type.value=="album" and b is None
            result={"qualification":"BASELINE_NO_ALBUM_RELATION","input_sha256":input_hashes,
                    "first":a.as_dict(),"second":None,"snapshot":await self.owner_snapshot(),
                    "external_fixture_boundaries":["SpotifyBackend._request"],
                    "native":"NOT_RUN","installed":"NOT_RUN","hardware":"NOT_RUN"}
            await self.stop()
            return result
        rows, fixtures = [], []
        for lang in ("en","nl","de","fr","es"):
            for persona in DJPersona:
                session = await self.start(locale=lang, persona=persona)
                a = await self.step(1)
                assert a and a.moment_type.value == "album", {"provider_calls":self.calls,"direction":session.session_direction.direction.value,"accepted":(await self.manager.async_get_active("profile-a")).last_accepted_media_identity,"state":session.broadcast.state.playback.state,"ledger":session.presence_ledger.suppression_reason}
                frozen = a.as_dict()
                ws, initial = await self.live()
                b = await self.step(2)
                assert b and isinstance(b.source_fact, AlbumContinuityFact), {"locale":lang,"persona":persona.value,"direction":session.session_direction.direction.value,"b_type":b.moment_type.value if b else None,"retained":len(session.published_album_context.albums),"budget":session.presence_ledger.total_published}
                assert a.as_dict() == frozen and b.moment_type.value == "track"
                envelopes=[]
                while True:
                    event = await asyncio.wait_for(ws.receive_json(), 5)
                    envelopes.append(event)
                    delivered = event.get("data", {}).get("payload", {}).get("dj_moment", {})
                    if delivered.get("moment_id") == b.moment_id:
                        break
                # All envelopes are actual transport output; source/provider internals never serialized.
                snapshots = await self.owner_snapshot()
                assert snapshots["playback"]["title"] == "Observed track 2"
                assert b.content in json.dumps(snapshots, ensure_ascii=False)
                deliveries = snapshots["native_delivery"]["admissions"]
                delivery = next(x for x in deliveries if x["moment_id"] == b.moment_id)
                assert delivery["current_display_allowed"] and not delivery["active_flow_display_allowed"]
                assert delivery["requires_spotify_attribution"]
                await ws.close()
                recovered_ws, recovery = await self.live()
                await recovered_ws.close()
                assert delivery["source_expires_at"] == next(x for x in
                    (await self.owner_snapshot())["native_delivery"]["admissions"] if x["moment_id"]==b.moment_id)["source_expires_at"]
                rows.append({"language":lang,"persona":persona.value,"album_then_track":True,
                             "native_current_only":True,"reconnect_deadline_unchanged":True,
                             "persona_setup":"HTTP start then existing Core Persona update" if persona is DJPersona.FESTIVAL_DJ else "ordinary HTTP start"})
                fixtures.append({"language":lang,"persona":persona.value,"snapshot_before":initial,
                                 "update_envelope":event,"update_envelopes":envelopes,"snapshot_after":snapshots,
                                 "reconnect":recovery})
        negatives = []
        session=await self.start(persona=DJPersona.FESTIVAL_DJ,direct_persona=True)
        assert session.session_direction.direction.value=="building_energy"
        await self.step(1)
        b=await self.step(2)
        assert not (b and isinstance(b.source_fact,AlbumContinuityFact))
        assert not session.published_album_context.albums
        negatives.append("ordinary_festival_start_preserves_building_energy_no_line")
        for name, changes in (("same_title_other_identity", {"album":"Y"*22}),
                              ("other_edition_remaster", {"album":"R"*22, "name":"Exact edition Remaster"}),
                              ("missing_identity", {"album":""}),
                              ("conflicting_date", {"date":"2002-03-04"}),
                              ("source_poor", {"date":""})):
            await self.start()
            await self.step(1)
            b = await self.step(2, **changes)
            assert not (b and isinstance(b.source_fact, AlbumContinuityFact))
            negatives.append(name)
        await self.start()
        await self.step(1)
        a = await self.manager.async_get_active("profile-a")
        count = len(a.broadcast.state.dj_moments)
        assert await self.step(1) is None
        assert len(a.broadcast.state.dj_moments) == count
        negatives.append("same_track_repeat")
        await self.start()
        await self.step(1)
        await self.start()
        b = await self.step(2)
        assert b and not isinstance(b.source_fact, AlbumContinuityFact)
        negatives.append("other_session")
        await self.start()
        await self.step(1)
        await self.presence("music_only")
        assert await self.step(2) is None
        await self.presence("presenter")
        b = await self.step(3)
        assert not (b and isinstance(b.source_fact, AlbumContinuityFact))
        negatives.append("off_on_no_catchup")
        races=[]
        for condition in ("off", "presence_aba", "track_change", "session_end"):
            await self.start()
            await self.step(1)
            entered, release = asyncio.Event(), asyncio.Event()
            async def external_musicbrainz(resolver, path, params=None, **kwargs):
                entered.set()
                await release.wait()
                return {"recordings":[]}
            with patch.object(SessionFactsResolver, "_get", external_musicbrainz):
                pending=asyncio.create_task(self.step(2, isrc="USABC0100001"))
                await asyncio.wait_for(entered.wait(), 5)
                if condition in ("off","presence_aba"):
                    await self.presence("music_only")
                    if condition=="presence_aba":
                        await self.presence("balanced")
                elif condition=="track_change":
                    self.raw=self.raw_track(3)
                    await self.observer._async_poll_spotify(self.observer._spotify_sessions["profile-a"])
                else:
                    await self.observer.async_stop("profile-a")
                    await self.manager.async_end(owner_profile_id="profile-a")
                release.set()
                await asyncio.wait_for(pending,5)
            active=await self.manager.async_get_active("profile-a")
            if active:
                assert not any(isinstance(m.source_fact,AlbumContinuityFact)
                               and m.source_fact.media_identity.endswith(f"{2:022d}")
                               for m in active.broadcast.state.dj_moments)
                if condition != "track_change":
                    assert not active.published_album_context.used_relations
            races.append({"condition":condition,"old_candidate_published":False,
                          "fixture_boundary":"external MusicBrainz request"})
        duration=None
        if os.environ.get("DJC_NARRATIVE_DURATION")=="1":
            session=await self.start(mode="presenter")
            started=time.monotonic()
            observations=0
            max_proofs=0
            for number in range(1,41):
                await self.step(number,album=f"{(number-1)//2:022d}")
                observations+=1
                active=await self.manager.async_get_active("profile-a")
                max_proofs=max(max_proofs,len(active.published_album_context.albums))
                assert len(active.published_album_context.observed_tracks)<=3
                assert len(active.published_album_context.used_relations)<=6
                assert len(active.published_album_context.connected_tracks)<=6
                await asyncio.sleep(1.5)
            duration={"real_elapsed_seconds":round(time.monotonic()-started,3),
                      "observations":observations,"max_album_proofs":max_proofs,
                      "consumed_relations":len(active.published_album_context.used_relations),
                      "modeled_spacing_seconds":200,"real_spacing_seconds":1.5,
                      "source_deadlines_real_monotonic":True,"catchup":False}
        matrix={}
        for mode in ("music_only","occasional","balanced","talkative","presenter"):
            session=await self.start(mode=mode)
            await self.step(1)
            b=await self.step(2)
            assert bool(b and isinstance(b.source_fact, AlbumContinuityFact)) == (mode != "music_only")
            matrix[mode]={"published":session.presence_ledger.total_published,
                          "album_connections":len(session.published_album_context.used_relations)}
        result={"qualification":"ISOLATED_HA_PROVIDER_BOUNDARY_RUNTIME_PASS","input_sha256":input_hashes,
                "twenty_persona_language_chains":rows,"negative_cases":negatives,
                "presence_matrix":matrix,"transport_fixtures":fixtures,"race_cases":races,"duration":duration,
                "external_fixture_boundaries":["SpotifyBackend._request","SessionFactsResolver._get (in-flight MusicBrainz cases only)"],
                "native":"NOT_RUN","installed":"NOT_RUN","hardware":"NOT_RUN"}
        await self.stop()
        return result

    async def stop(self):
        active=await self.manager.async_get_active("profile-a")
        if active and self.owner:
            response=await self.owner["client"].post("/api/djconnect/v1/session/end",
                headers=self.owner["headers"],json={**self.owner["identity"],"session_id":active.session_id})
            assert response.status==200, await response.json()
        else:
            await self.observer.async_stop("profile-a")
        if self.source_patch is not None:
            self.source_patch.stop()
            self.source_patch = None

    def register_browser(self):
        async def setup(request):
            session = await self.start()
            return web.json_response({"kind":"vibecast_handoff","version":1,"session_id":session.session_id,
                "broadcast_token":session.broadcast.broadcast_token,"ha_url":"https://localhost:18233","locale":"nl"})
        async def publish(request):
            moment = await self.step(int(request.query["number"]))
            settle = getattr(self, "settle_art", None)
            if settle is not None:
                await settle()
            return web.json_response({"moment":moment.as_dict() if moment else None,
                                      "snapshot":await self.owner_snapshot()})
        async def end(request):
            await self.stop()
            return web.json_response({"ended":True})
        async def presence(request):
            return web.json_response(await self.presence(request.query["value"]))
        for name, handler in (("setup",setup),("publish",publish),("end",end),("presence",presence)):
            self.hass.http.app.router.add_get("/__album_lab/"+name,handler)
        async def serve(client, identity, headers):
            self.owner={"client":client,"identity":identity,"headers":headers}
            lab=Path(os.environ["DJC_LAB_ROOT"])
            tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(lab/"server.pem",lab/"server-key.pem")
            await web.TCPSite(client.server.runner,"127.0.0.1",18233,ssl_context=tls).start()
            static=web.Application()
            async def index(request):
                return web.Response(text=(lab/"build/cast/index.html").read_text(),content_type="text/html",
                                    headers={"Cache-Control":"no-store","Referrer-Policy":"no-referrer"})
            static.router.add_get("/",index)
            runner=web.AppRunner(static)
            await runner.setup()
            await web.TCPSite(runner,"127.0.0.1",18234,ssl_context=tls).start()
            (lab/"browser-ready.json").write_text(json.dumps({"local":18233,"cast":18234}))
            try:
                await asyncio.Event().wait()
            finally:
                await runner.cleanup()
                await self.stop()
        return serve
