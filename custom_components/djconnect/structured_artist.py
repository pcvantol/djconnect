"""Closed typed artist operations; structural addresses never grant factual truth.

EN/NL qualification uses the same explicitly configured public HA task as
playback. Original complete sources and all semantic/word/date guards remain.
HA returns parsed data: this ABI cannot observe original duplicate JSON keys.
"""
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def _data(prompt):
    if type(prompt) is not str or len(prompt.encode()) > 24576:
        raise ValueError("artist_task_prompt")
    _, sep, raw = prompt.partition("\nData:\n")
    value = json.loads(raw) if sep else None
    if type(value) is not dict:
        raise ValueError("artist_task_prompt")
    return value


@dataclass(frozen=True)
class ArtistTask:
    operation: str
    prompt_sha256: str
    anchors: tuple[str, ...] = ()
    drafts: tuple[tuple[int, str, tuple[str, ...]], ...] = ()

    def witness(self):
        value = {"schema_version": 1, "operation": self.operation,
            "prompt_sha256": self.prompt_sha256,
            "anchors": list(self.anchors),
            "drafts": [[i, sha, list(words)] for i, sha, words in self.drafts]}
        return {**value, "binding_sha256": _digest(value)}


def generation(prompt, corpus):
    from .narration_brief import ArtistAnchorCorpus
    if type(corpus) is not ArtistAnchorCorpus:
        raise ValueError("artist_task_corpus")
    corpus.validate()
    data = _data(prompt)
    if data.get("literal_anchors") != corpus.projection():
        raise ValueError("artist_task_corpus")
    return ArtistTask("artist_generation_v1", hashlib.sha256(prompt.encode()).hexdigest(),
                      tuple(row["id"] for row in corpus.projection()))


def review(prompt, words, drafts):
    from .artist_review_words import AnswerWordReview
    if type(words) is not AnswerWordReview or words != AnswerWordReview.capture(drafts):
        raise ValueError("artist_task_drafts")
    data = _data(prompt)
    if _digest(data.get("drafts")) != _digest(words.records()):
        raise ValueError("artist_task_drafts")
    return ArtistTask("artist_word_review_v1", hashlib.sha256(prompt.encode()).hexdigest(),
        drafts=tuple((row["index"], row["sha256"], tuple(w[0] for w in row["answer_words"]))
                     for row in words.records()))


current_operation: ContextVar[ArtistTask | None] = ContextVar(
    "djconnect_structured_artist_operation", default=None)


def schema(operation):
    """Only closed Core operations, never caller-provided schema or verdicts."""
    import probatio as p
    if type(operation) is not ArtistTask:
        raise ValueError("artist_task_operation")
    def string(maximum=1200):
        return p.All(str, p.Length(min=1, max=maximum))
    def exact(value):
        return p.All(type(value), p.In([value]))
    def array(item, minimum, maximum):
        return p.All([item], p.Length(min=minimum, max=maximum))
    if operation.operation == "artist_generation_v1":
        if not 1 <= len(operation.anchors) <= 32 or operation.drafts:
            raise ValueError("artist_task_operation")
        return p.Schema({p.Required("schema"): exact("artist_evidence_drafts_v1"),
            p.Required("drafts"): array({
                p.Required("anchors"): array(p.All(str, p.In(operation.anchors)), 1, 3),
                p.Required("text"): string(8192)}, 1, 1)})
    if (operation.operation != "artist_word_review_v1" or operation.anchors
            or not 1 <= len(operation.drafts) <= 2):
        raise ValueError("artist_task_operation")
    from .ask_dj.biographical_dates import KEYS, SCHEMA
    work = {p.Required(key): string() for key in
            ("claim", "event_anchor", "year", "source_id", "quote")}
    bio = {p.Required(key): exact(SCHEMA) if key == "schema" else string() for key in KEYS}
    rows = []
    for index, sha, addresses in operation.drafts:
        if type(index) is not int or not addresses or len(addresses) > 512:
            raise ValueError("artist_task_operation")
        # Keep provider schema size bounded even for the existing512-word cap.
        # Exact membership/order/coverage still belongs to AnswerWordReview.decode.
        address = p.All(str, p.Length(max=16),
            p.Match(r"^d" + str(index) + r"w(?:0|[1-9][0-9]{0,2})$"))
        verdict = {
            p.Required("review_schema"): exact("source_answer_ids_review_v1"),
            p.Required("supported"): bool, p.Required("language_ok"): bool,
            p.Required("style_ok"): bool,
            p.Required("unsupported_claims"): array(string(), 0, 3),
            p.Required("claim_checks"): array({
                p.Required("answer_from"): address, p.Required("answer_to"): address,
                p.Required("kind"): p.All(str, p.In(("fact", "relationship", "dj_appreciation"))),
                p.Required("evidence_ids"): array(string(512), 0, 1)}, 0, 24),
            p.Required("temporal_claims"): array(p.Any(work, bio), 0, 8)}
        rows.append({p.Required("index"): exact(index), p.Required("sha256"): exact(sha),
                     p.Required("review"): verdict})
    return p.Schema({p.Required("draft_reviews"): array(
        rows[0] if len(rows) == 1 else p.Any(*rows), len(rows), len(rows))})
