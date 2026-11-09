"""Closed B transitions over existing pairing and the sole Runtime lock.

No HTTP registration, projection, source fetch or capability advertisement here.
Transport must bound bytes before decoding and invoke the returned release fence
immediately before releasing any response, including after awaited preparation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import re
import hashlib
from typing import Callable

from .display_admission import DisplayAdmissionError
from .display_authority import resolve_display_owner
from .display_origin import selected_ha_origin, ENTRY_PATH

_BROWSER = {"issuer_epoch", "claim_id", "claim_secret", "browser_generation", "browser_nonce"}
_GRANT = {"issuer_epoch", "display_id"}
_SHAPES = {
    "owner/context": ({"identity"}, {"session_id"}),
    "owner/resolve": ({"identity", "code"}, set()),
    "owner/approve": ({"identity", "session_id", "issuer_epoch", "claim_id",
                       "browser_generation", "code", "share"}, set()),
    "owner/revoke": ({"identity", "session_id", "share_id"},
                     {"display_id", "issuer_epoch", "connection_generation"}),
    "claim": ({"browser_nonce"}, set()),
    "collect": (_BROWSER, set()), "cancel": (_BROWSER, set()),
    "renew": (_GRANT | {"renew_sequence"}, set()),
    "leave": (_GRANT, set()),
    "snapshot": (_GRANT, set()),
    "artwork": (_GRANT | {"reference"}, set()),
}


@dataclass(frozen=True, slots=True, repr=False)
class DisplayResult:
    payload: dict
    release: Callable[[], None]
    complete: Callable[[], None] = lambda: None
    media: tuple[bytes, str] | None = None


def _shape(action, payload):
    if action not in _SHAPES or not isinstance(payload, dict):
        raise DisplayAdmissionError("display_code_invalid", 400)
    if type(payload.get("contract_version")) is not int or payload["contract_version"] != 1:
        raise DisplayAdmissionError("display_contract_unsupported", 400)
    required, optional = _SHAPES[action]
    fields = set(payload) - {"contract_version"}
    if not required <= fields or fields - required - optional:
        raise DisplayAdmissionError("display_code_invalid", 400)
    if action == "owner/revoke" and fields & {"issuer_epoch", "connection_generation"}:
        if not {"issuer_epoch", "connection_generation", "display_id"} <= fields:
            raise DisplayAdmissionError("display_code_invalid", 400)
    for key, value in payload.items():
        if key in {"contract_version", "identity", "share"}:
            continue
        if key in {"renew_sequence", "connection_generation"}:
            if type(value) is not int or not 1 <= value <= 2**53 - 1:
                raise DisplayAdmissionError("display_code_invalid", 400)
        elif not isinstance(value, str) or not 0 < len(value) <= 256:
            raise DisplayAdmissionError("display_code_invalid", 400)
        elif key == "reference" and re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise DisplayAdmissionError("display_code_invalid", 400)
        elif key == "code" and re.fullmatch(r"[0-9]{6}", value) is None:
            raise DisplayAdmissionError("display_code_invalid", 400)
        elif key in _BROWSER - {"code"} or key == "display_id":
            if re.fullmatch(r"[A-Za-z0-9_-]{43}", value) is None:
                raise DisplayAdmissionError("display_code_invalid", 400)


class DisplayAdmissionService:
    def __init__(self, hass, manager):
        self.hass, self.manager = hass, manager

    def _origin(self, expected=None):
        actual = selected_ha_origin(self.hass)
        if actual is None:
            raise DisplayAdmissionError("display_external_url_unavailable", 503)
        if expected is not None and actual != expected:
            raise DisplayAdmissionError("display_context_changed", 409)
        return actual

    def _sync_origin(self, selected):
        # Invoked under the existing Runtime lock. An origin change cannot
        # transfer a pending claim, consent, bearer or connection to a new host.
        state = self.manager._display_admission
        if state.selected_origin != selected:
            state.clear()
            state.selected_origin = selected

    async def post(self, action, payload, *, headers, origins, source):
        _shape(action, payload)
        async with self.manager._lock:
            selected = selected_ha_origin(self.hass)
            self._sync_origin(selected)
            self._origin(selected)
        owner_action = action.startswith("owner/")
        # Absence is permitted only for an owner action that still authenticates
        # normal pairing below. Duplicate/null/foreign Origin never authenticates.
        if tuple(origins) != (selected,) and not (owner_action and not origins):
            raise DisplayAdmissionError("display_origin_denied", 403)
        owner = None
        targeted_stop = action == "owner/revoke" and "connection_generation" in payload
        if owner_action:
            # A sibling paired device may resolve its playback provider through
            # a different entry. The live writer validates the original source.
            owner_session = "" if targeted_stop else payload.get("session_id", "")
            _context, owner = await resolve_display_owner(self.hass, payload["identity"],
                headers, self.manager, session_id=owner_session)
            original_owner = owner
            origin_revoked = False
            def origin_bound_owner():
                nonlocal origin_revoked
                origin_revoked = (origin_revoked or not original_owner.valid()
                    or selected_ha_origin(self.hass) != selected)
                return not origin_revoked
            owner = replace(owner, stamp=hashlib.sha256((owner.stamp + selected).encode()).hexdigest(),
                            current=origin_bound_owner)
        async with self.manager._lock:
            current = selected_ha_origin(self.hass)
            self._sync_origin(current)
            self._origin(selected)
            state = self.manager._display_admission
            if owner is not None and not owner.valid():
                raise DisplayAdmissionError("display_context_changed", 403)
            media = None
            args = {key: value for key, value in payload.items()
                    if key not in {"contract_version", "identity", "session_id"}}
            guard = owner.valid if owner else lambda: True
            def complete():
                return None
            if action == "owner/context":
                from .display_delivery import display_live_hub

                active = self.manager.current_active(owner.profile_id)
                active_id = active.session_id if active else None
                hub = display_live_hub(self.manager)
                live_displays = hub.live_displays(owner.profile_id, active_id)

                def context_current():
                    now_active = self.manager.current_active(owner.profile_id)
                    return (owner.valid() and now_active is active
                            and hub.live_displays(owner.profile_id, active_id) == live_displays)

                guard = context_current
                result = {"session_id": active.session_id if active else None,
                    "display_entry_url": selected + ENTRY_PATH,
                    "route_trust": "paired_owner_response",
                    "output_status_consent_supported": True,
                    "issuer_epoch": state.issuer_epoch,
                    "live_display_status": {
                        "version": 1,
                        "observation_revision": hub.next_observation_revision(),
                        "displays": [{"display_id": display_id, "share_id": share_id,
                                      "connection_generation": generation}
                                     for display_id, share_id, generation in live_displays],
                    },
                    "limits": {"claim_seconds": 120, "lease_seconds": 60,
                               "share_seconds_default": 7200, "displays_per_share": 8}}
                share = next((share for share in state._shares.values()
                    if active and share.owner.session_id == active.session_id
                    and share.deadline > state._clock() and share.owner.valid()), None)
                if share:
                    result.update(share_id=share.share_id, share_generation=share.generation,
                                  expires_in=max(0, share.deadline - state._clock()))
            elif action == "owner/resolve":
                result = state.resolve(owner=owner, **args)
                claim = state._claims[result["claim_id"]]
                def guard():
                    return (owner.valid() and state._claims.get(claim.claim_id) is claim
                                    and claim.deadline > state._clock() and claim.owner is None)
            elif action == "owner/approve":
                result = state.approve(owner=owner, **args)
                approved_share = state._shares[result["share_id"]]
                approved_id = result["display_id"]
                def guard():
                    return (owner.valid() and approved_share.owner.valid()
                                    and state._shares.get(approved_share.share_id) is approved_share
                                    and approved_share.deadline > state._clock()
                                    and (approved_id in state._displays or any(c.display_id == approved_id
                                        and c.deadline > state._clock() for c in state._claims.values())))
            elif action == "owner/revoke":
                generation = args.pop("connection_generation", None)
                result = {}
                if generation is not None:
                    from .display_delivery import display_live_hub

                    active = self.manager.current_active(owner.profile_id)
                    if active is None or active.session_id != payload["session_id"]:
                        raise DisplayAdmissionError("display_context_changed", 403)
                    hub = display_live_hub(self.manager)
                    if (args.pop("issuer_epoch") != state.issuer_epoch
                            or (args["display_id"], args["share_id"], generation) not in
                            hub.live_displays(owner.profile_id, active.session_id)):
                        raise DisplayAdmissionError("display_context_changed", 409)
                    paired_owner = owner

                    def stop_authority_current():
                        return (paired_owner.valid()
                                and self.manager.current_active(paired_owner.profile_id) is active)
                    owner = replace(owner, session_id=active.session_id, current=stop_authority_current)
                    guard = owner.valid
                state.revoke(owner=owner, **args)
                if generation is not None:
                    result["observation_revision"] = hub.next_observation_revision()
            elif action == "claim":
                result = state.create_claim(source=source, **args)
                claim = state._claims[result["claim_id"]]
                def guard():
                    return (state._claims.get(claim.claim_id) is claim
                                    and claim.deadline > state._clock())
            elif action in {"collect", "cancel"}:
                result = getattr(state, action)(**args) or {}
                if action == "collect" and result.get("state") == "admitted":
                    display = state._displays[result["display_id"]]
                    def guard():
                        return (state._displays.get(display.display_id) is display
                                            and display.owner.valid() and display.lease_deadline > state._clock()
                                            and (share := state._shares.get(display.share_id)) is not None
                                            and share.owner.valid() and share.deadline > state._clock())
            else:
                token = headers.get("Authorization", "")
                if not isinstance(token, str) or not token.startswith("Bearer djcd_"):
                    raise DisplayAdmissionError("display_grant_invalid", 401)
                args["token"] = token.removeprefix("Bearer ")
                if action == "artwork":
                    from .display_delivery import display_live_hub, qualified_artwork
                    from .display_projection import projection_release_guard, shared_snapshot

                    reference = args.pop("reference")
                    display = state.authorize(**args)
                    active = self.manager.current_active(display.owner.profile_id)
                    found = qualified_artwork(active, display, state)
                    flow_item_id = None
                    flow_guard = None
                    if found is None or reference != found[0]:
                        found = None
                        for item_id in getattr(getattr(active, "broadcast", None), "display_flow_artwork", {}):
                            match = qualified_artwork(active, display, state, flow_item_id=item_id)
                            if match is not None and match[0] == reference:
                                found, flow_item_id = match, item_id
                                break
                        if found is None:
                            raise DisplayAdmissionError("display_artwork_unavailable", 404)
                        snapshot = shared_snapshot(active, display, state)
                        if not any(item.get("artwork", {}).get("reference") == reference
                                   for item in snapshot["shared_flow"]):
                            raise DisplayAdmissionError("display_artwork_unavailable", 404)
                        flow_guard = projection_release_guard(active, display, state, snapshot)
                    asset = found[1]

                    def guard():
                        current = self.manager.current_active(display.owner.profile_id)
                        match = qualified_artwork(current, display, state, flow_item_id=flow_item_id)
                        return (match is not None and match[0] == reference and match[1] is asset
                                and (flow_guard is None or flow_guard()))
                    complete = display_live_hub(self.manager).reserve_artwork(display.display_id)
                    media = (asset.body, asset.mime)
                    result = {}
                elif action == "snapshot":
                    from .display_projection import shared_snapshot, projection_release_guard
                    from .display_delivery import display_live_hub
                    display = state.authorize(**args)
                    active = self.manager.current_active(display.owner.profile_id)
                    if active is None:
                        raise DisplayAdmissionError("display_grant_invalid", 401)
                    complete = display_live_hub(self.manager).reserve_projection(display.display_id)
                    try:
                        snapshot = shared_snapshot(active, display, state)
                    except BaseException:
                        complete()
                        raise
                    result = {"snapshot": snapshot}
                    content_current = projection_release_guard(active, display, state, snapshot)
                    def guard():
                        return (self.manager.current_active(display.owner.profile_id) is active
                            and content_current())
                else:
                    result = getattr(state, action)(**args) or {}
                if action == "renew":
                    display = state._displays[args["display_id"]]
                    def guard():
                        return (state._displays.get(display.display_id) is display
                                            and display.owner.valid() and display.lease_deadline > state._clock()
                                            and (share := state._shares.get(display.share_id)) is not None
                                            and share.owner.valid() and share.deadline > state._clock())
            epoch = state.issuer_epoch
            wall = datetime.now(timezone.utc)
            result = {"success": True, "contract_version": 1, **result}
            for key, value in tuple(result.items()):
                if key.endswith("expires_in"):
                    result[key.removesuffix("_in") + "_at"] = (wall + timedelta(seconds=value)).isoformat()

            def release():
                valid = guard()
                self._origin(selected)
                if state.issuer_epoch != epoch or not valid:
                    raise DisplayAdmissionError("display_context_changed", 403)

            try:
                release()
            except BaseException:
                complete()
                raise
            return DisplayResult(result, release, complete, media)
