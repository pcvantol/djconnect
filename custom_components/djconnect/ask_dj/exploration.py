"""Selected-contribution exploration on the existing Ask DJ read boundary."""
from __future__ import annotations

import re

MORE_TEXT = {
    "en": "Tell me more",
    "nl": "Vertel meer",
    "de": "Erzähl mir mehr",
    "fr": "Dis-m’en plus",
    "es": "Cuéntame más",
}
ANGLES = {
    "biography": "music biography documented history",
    "members": "band members interview",
    "live_history": "live performance concert history",
    "recording": "recording studio interview",
    "composition": "songwriting composition interview",
    "production": "record producer studio interview",
    "discography": "albums discography official",
    "current_events": "official concerts tour current dates",
}


def more_request(text):
    """Fast common affordance, not the free-language interpreter's whitelist."""
    return bool(re.fullmatch(
        r"(?:tell me more|vertel (?:me )?meer|erz[aä]hl(?:e)? (?:mir )?mehr|"
        r"dis[- ]m['’]en plus|cu[eé]ntame m[aá]s)[.!? ]*", text.strip(), re.I))


def capability():
    return {"version": 1, "operation": "ask_dj/message",
            "context": ["selected_entry", "selected_moment"],
            "generic_questions": dict(MORE_TEXT),
            "attribute_required": False, "effect": "informational",
            "subject_authority":"qualified_selected_public_context",
            "unqualified_context":"existing_source_unavailable_response",
            "client_gesture_owner":"client", "maximum_agent_calls":3}


def admitted_subject(subject, angle, context):
    """An interpreter chooses public context; it cannot manufacture authority."""
    from .public_research import safe_subject
    if angle not in ANGLES or not isinstance(context, dict):
        return None
    if context.get("basis") != "cc0_normalized_fields_v1":
        return None
    name = safe_subject(subject, qualified=True)
    if not name or len(name) > 120:
        return None
    subjects = context.get("subjects", [])
    names = [s.get("name") for s in subjects if isinstance(s, dict)]
    if names:
        # Full identities and their roles are resolved by Core, not a guessed
        # partial name, client prose, image label or model's preferred band.
        return next((n for n in names if isinstance(n, str) and n.casefold() == name.casefold()), None)
    # A word in an old excerpt is not a canonical identity ("Brian" in
    # "Brian Eno", for example). Generic questions need no caller attribute,
    # but their subject must still come from Core's qualified full identities.
    return None


def named_in_question(subject, text):
    """A full user name can contain a small typo, never missing name parts."""
    if re.search(r"(?<!\w)"+re.escape(subject)+r"(?!\w)",text,re.I):
        return True
    names=re.findall(r"[^\W\d_]+",subject.casefold())
    words=re.findall(r"[^\W\d_]+",text.casefold())
    if not names or (len(names)==1 and len(names[0])<4):
        return False
    def distance(left,right):
        if left==right:
            return 0
        if min(len(left),len(right))<4 or abs(len(left)-len(right))>2:
            return 3
        row=list(range(len(right)+1))
        for i,a in enumerate(left,1):
            new=[i]
            for j,b in enumerate(right,1):
                new.append(min(new[-1]+1,row[j]+1,row[j-1]+(a!=b)))
            row=new
        return row[-1]
    return any(sum(distance(a,b) for a,b in zip(names,words[i:i+len(names)],strict=True))<=2
               for i in range(len(words)-len(names)+1))


async def research_response(hass, runtime, text, plan, *, recent_reference=None):
    from .dialogue import current_turn
    from . import _informational_assist_response
    turn = current_turn.get()
    if turn is None:
        return None
    if plan.reference == "named":
        from .public_research import safe_subject
        subject=safe_subject(plan.subject)
        # The model may select an angle, but the complete public name must
        # actually be in this question. No invented fallback to another artist.
        if not subject or not named_in_question(subject,text):
            return None
        turn.public_query_candidate = subject
        turn.source_context={}
        turn.selected_read_context=None
        turn.dependencies.clear()
        turn.reset_topic=True
        turn.explicit_research_subject=True
    elif plan.reference == 'recent':
        from .dialogue import PublicQueryReference
        if (type(recent_reference) is not PublicQueryReference
                or turn.frame.public_query_reference is not recent_reference
                or recent_reference.scope != turn.scope or recent_reference.thread_id != turn.thread_id):
            return None
        subject = recent_reference.subject
        turn.source_context = {}
        turn.selected_read_context = None
        turn.dependencies.clear()
    else:
        if turn.selected_read_context is None:
            return None
        subject = admitted_subject(plan.subject, plan.angle, turn.source_context)
    if not subject:
        return None
    await turn.guard()
    turn.interpreted_context_research = True
    return await _informational_assist_response(hass, runtime, text, {}, {}, {}, [],
        research_subject=subject, research_angle=plan.angle, contextual_research=True)
