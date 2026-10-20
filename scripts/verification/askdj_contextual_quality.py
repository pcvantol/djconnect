"""Actual-answer editorial pilot in the existing isolated paired HA harness.

Public research and the configured HA Conversation provider are real. Music
catalog I/O and the owner are synthetic; no installed/native/audio claim.
Mechanical checks never certify warmth or narrative quality.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os

from scripts.verification.askdj_contextual_golden import ACTIVE_CASE

QUESTIONS = {
    "en":"Tell me about Nirvana: the people in the band and a remarkable live performance. Give me the story, not just credits.",
    "nl":"Vertel me over Nirvana: de mensen in de band en een bijzonder optreden. Neem me mee in het verhaal, niet alleen de credits.",
    "de":"Erzähl mir von Nirvana: den Menschen in der Band und einem besonderen Liveauftritt. Nimm mich mit in die Geschichte, statt nur Credits aufzuzählen.",
    "fr":"Raconte-moi Nirvana : les membres du groupe et un concert marquant. Fais-moi découvrir leur histoire, pas seulement leurs crédits.",
    "es":"Háblame de Nirvana: los miembros de la banda y una actuación memorable. Cuéntame la historia, no solo los créditos.",
}
MORE = {"en":"Tell me more","nl":"Vertel meer","de":"Erzähl mir mehr",
        "fr":"Dis-m’en plus","es":"Cuéntame más"}
STYLES = (("home_dj","chill"),("radio_dj","groove"),("club_dj","energy"),
          ("festival_dj","party"),("home_dj","groove"))


def cases():
    return [{"id":"quality-"+kind+"-"+locale,"kind":kind,"language":locale,
        "question":MORE[locale] if kind=="selected" else QUESTIONS[locale] if kind=="band" else "accepted Mood transition",
        "persona":"radio_dj" if kind=="selected" else persona,"mood":"groove" if kind=="selected" else mood}
        for kind in ("selected","band","mood")
        for locale,(persona,mood) in zip(QUESTIONS,STYLES,strict=True)]


def manifest_digest():
    return hashlib.sha256(json.dumps(cases(),sort_keys=True).encode()).hexdigest()


def check_answer(case, response):
    findings=[]
    text=response.get("text","")
    if not response.get("success"):
        findings.append("response_not_accepted")
    if not response.get("is_generated_text"):
        findings.append("generated_answer_missing")
    if not text.rstrip().endswith("?"):
        findings.append("closing_question_missing")
    if case["kind"]!="mood":
        if response.get("knowledge_basis")!="fetched_public_music_research_v1":
            findings.append("researched_answer_unqualified")
        if len(text)<(400 if case["kind"]=="band" else 180):
            findings.append("answer_too_sparse_for_requested_story")
        if not response.get("sources"):
            findings.append("actual_sources_missing")
    if response.get("playback_actions") or response.get("action") not in (None,"none"):
        findings.append("unexpected_effect_or_concrete_offer")
    return findings


async def run(*,ask,call,start,end,get_history,mutations,model_receipts):
    rows=[]
    locales=os.environ.get('DJC_QUALITY_LOCALES','en,nl,de,fr,es').split(',')
    if not locales or len(set(locales))!=len(locales) or any(locale not in QUESTIONS for locale in locales):
        raise ValueError('invalid_actual_quality_locales')
    kinds=os.environ.get('DJC_QUALITY_KINDS','selected,band,mood').split(',')
    if (not kinds or len(set(kinds)) != len(kinds) or any(kind not in {'selected','band','mood'} for kind in kinds)
            or ('mood' in kinds and 'band' not in kinds)):
        raise ValueError('invalid_actual_quality_kinds')
    seed_mode=os.environ.get('DJC_QUALITY_SEED_ONLY','0')
    if seed_mode not in {'0','1'} or (seed_mode=='1' and (kinds!=['selected'] or len(locales)!=1)):
        raise ValueError('invalid_actual_quality_seed_only_scope')
    seed_only=seed_mode=='1'
    requested=[c for c in cases() if c['language'] in locales and c['kind'] in kinds]
    # One actual selected composer publication; its live owner remains intact.
    seed=ACTIVE_CASE.set('quality-selected-seed')
    active,moment=None,None
    try:
        if 'selected' in kinds:
            active,moment,_=await start("quality-selected",language=locales[0])
    except Exception as exc:
        rows.extend({**case,'findings':['selected_publication_unavailable:'+type(exc).__name__]}
                    for case in requested if case['kind']=='selected')
    finally:
        ACTIVE_CASE.reset(seed)
    selection=({'session_id':active.session_id,'moment_id':moment.moment_id} if moment is not None else None)
    publication=({'moment_id':moment.moment_id,'text':moment.content} if seed_only and moment is not None else None)
    try:
        for case in (c for c in requested if c["kind"]=="selected" and selection is not None):
            if seed_only:
                # A publication recheck is not a selected-contribution request.
                # Retain the missing acceptance step instead of manufacturing PASS.
                rows.append({**case,'findings':['selected_followup_not_exercised']})
                continue
            await call("ask_dj/history/clear",{},label=case["id"]+"-clear")
            token=ACTIVE_CASE.set(case["id"])
            before=len(model_receipts)
            try:
                reply=await ask(case["question"],case["id"],{"selected_moment":selection},language=case["language"])
                rows.append({**case,"response":reply,"findings":check_answer(case,reply),
                             "paid_attempts":len(model_receipts)-before})
            except Exception as exc:
                rows.append({**case,"findings":["owner_or_transport:"+type(exc).__name__]})
            finally:
                ACTIVE_CASE.reset(token)
    finally:
        if active is not None:
            await end(active,"quality-selected")
    for case in (c for c in requested if c["kind"]=="band"):
        await call("ask_dj/history/clear",{},label=case["id"]+"-clear")
        active,_,_=await start("quality-band-"+case["language"],mood=case["mood"],
            persona=case["persona"],language=case["language"])
        token=ACTIVE_CASE.set(case["id"])
        before=len(model_receipts)
        try:
            reply=await ask(case["question"],case["id"],{"session_id":active.session_id},language=case["language"])
            findings=check_answer(case,reply)
            style=reply.get("conversation",{}).get("style",{})
            if (style.get("persona"),style.get("mood"))!=(case["persona"],case["mood"]):
                findings.append("confirmed_style_mismatch")
            rows.append({**case,"response":reply,"findings":findings,"paid_attempts":len(model_receipts)-before})
            moodcase=next((c for c in requested if c["kind"]=="mood" and c["language"]==case["language"]),None)
            if moodcase is None:
                continue
            new_mood="party" if active.selected_mood!="party" else "chill"
            before=len(model_receipts)
            accepted=await call("session/mood",{"contract_version":1,"session_id":active.session_id,
                "selected_mood":new_mood,"expected_mood_revision":active.mood_revision},label=moodcase["id"])
            request_id=(accepted.get("mood_music_feedback") or {}).get("request_id")
            feedback=None
            for _ in range(160):
                messages=(await get_history()).get("messages",[])
                feedback=next((m for m in messages if m.get("role")=="assistant"
                    and m.get("client_message_id")==request_id),None)
                if feedback:
                    break
                await asyncio.sleep(.5)
            findings=[]
            if feedback is None:
                findings.append("mood_feedback_not_published")
            else:
                if not feedback.get("text","").rstrip().endswith("?"):
                    findings.append("mood_direction_question_missing")
                if feedback.get("origin")!="mood_change":
                    findings.append("setting_event_origin_missing")
            rows.append({**moodcase,"mood":new_mood,"response":feedback or {},"findings":findings,
                         "paid_attempts":len(model_receipts)-before})
        except Exception as exc:
            rows.append({**case,"findings":["owner_or_transport:"+type(exc).__name__]})
        finally:
            ACTIVE_CASE.reset(token)
            await end(active,"quality-band-"+case["language"])
    return {"schema_version":1,"suite":"contextual_dj_actual_answers_v1","manifest_sha256":manifest_digest(),
        "qualification":"REAL_HA_PAIRED_ASSIST_PUBLIC_RESEARCH_SYNTHETIC_MUSIC_OWNER",
        "requested_case_ids":[c['id'] for c in requested],
        "selected_probe_scope":"publication_only_partial" if seed_only else "complete_selected_request",
        "selected_seed_publication":publication,
        "cases":rows,"paid_model_calls":len(model_receipts),"usage":model_receipts,
        "mechanical_status":"PASS" if len(rows)==len(requested) and not mutations and all(not r["findings"] for r in rows) else "FAIL",
        "editorial_status":"REQUIRES_INDEPENDENT_ACTUAL_ANSWER_REVIEW",
        "installed_native_audible":"NOT_RUN"}
