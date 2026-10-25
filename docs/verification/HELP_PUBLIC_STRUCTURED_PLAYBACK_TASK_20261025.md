# Optional public Home Assistant task for playback replies

This source adds an explicit, optional `assist_structured_task_id` selection alongside Assist. An empty selection retains the existing conversation path. A selected task is strict: missing, retired, unsafe, changed or incompatible configuration fails closed, without selecting a preferred task or silently switching back to conversation. It creates no task, provider account, credential or installed configuration.

Only generation of a verified `PlaybackRequestBrief` may use this path. Interpretation, independent whole-answer review, public artist research and ordinary freeform Ask DJ retain their existing routes. Catalogue examples are not an exact-question whitelist. The original100 questions, routes, language/style/grounding judges, source/effect guards and publication gates are unchanged.

## Actual supported boundary

The implementation uses the exported `homeassistant.components.ai_task.async_generate_data` API, with an explicit entity ID, a Core-owned public `probatio.Schema`, `attachments=None` and `llm_api=None`. It never calls a provider's private entity method or SDK client. The shared helper lifecycle dependency is qualified specifically against HA2026.10.0; other versions fail closed until independently qualified.

The task must be the exact official OpenAI task entity, enabled and available, in the same actual loaded provider config entry as the selected qualified conversation entity. Both registry records and current subentry objects must match. Task model, token bound and reasoning effort must match the selected conversation; store, web search and code interpreter must explicitly be false. Flex-tier retries are excluded. Both complete public option maps and entry/registry revision timestamps are captured and checked again after the await, including update-and-restore changes. No unsafe option is overridden at call time.

The actual task uses HA's own system-prompt template, including current date/time; it does not use the conversation entity's configured static prompt. This is a distinct, explicitly selected context boundary. The complete original Core language, Persona, Mood, source and truth instructions remain the task instructions. Isolated tests using an official task do not establish that any installed task is available or approved.

## Typed result and unchanged content admission

The public API receives a schema with the literal `playback_role_gaps_v3` enum, one to two drafts, exact required `gaps` role keys and string values. Role names come only from the original Core slot inventory. Actual SDK-boundary qualification must verify strict JSON schema, nested closed objects and list cardinality; a prompt requesting JSON is not such proof.

HA parses the provider's JSON before returning `GenDataTaskResult.data`. This is a new internal typed-result ABI: original raw duplicate JSON keys cannot be observed through that API. No claim of raw-envelope equivalence is made. All legacy raw duplicate-key rejection remains. The official typed result is bounded and frozen, then the unchanged named-map/literal-gap decoder checks the complete batch before normalization: exact roles, types, characters, original slot order, status punctuation, length and scope. No missing word is reconstructed and no model prose is repaired. The independent whole-answer hash, grounding, language and style review still decides publication.

One task generation consumes the same shared turn-call allowance as conversation generation. Interpretation, generation and review retain the existing maximum, original20-second post-dispatch allowance and23-second delivery fence. No retry, extra allowance, reset or alternate agent is introduced. The qualification SDK observer reserves attempts before I/O, including failed or cancelled attempts; returned receipts are counted separately.

## Cancellation and resource ownership

The coroutine directly awaiting the public task owns cleanup, using the pinned public chat-session helper and a ContextVar token. A separate `wait_for` task would hide the task's active session during cancellation, so this route uses same-task timeout handling. Only the new session owned by this call may be cleaned; prior sessions are excluded. Cleanup restores the prior context unconditionally, and a cleanup error cannot replace an original provider error or cancellation. A swallowed cancellation still prevents returning a reply.

The public cleanup releases chat-log callbacks; HA may retain bounded empty session metadata until its normal cleanup. No global session dictionary is deleted or reset. The official task's own last-activity state is a local HA effect, not a provider/device or playback effect.

## Qualification and remaining gates

Cost-free real-HA controls cover the exact official conversation/task binding, provider schema, Core compilation, unsafe/missing configuration, late revocation and update-and-restore, primary error plus cleanup error, cancellation plus cleanup error, a swallowed cancellation, an unoffered tool response, prior-session ownership, and a mixed conversation/task maximum of three calls with the fourth denied before SDK entry. These use synthetic owned configuration and intercepted SDK responses, without network or paid model calls. Their source/hash/cleanup receipts remain separate from content-quality qualification.

The original99a2 development run40210947501 remainsFAILURE19PASS5FAIL/63reserved63completed. Its two shape failures and three original artist support/style negatives remain failures; structured syntax does not fix unsupported or inadequate prose. Earlier failures, reservations and original artifacts remain preserved.

No catalogue release follows from these cost-free controls. Normal protected source qualification must precede a new bounded paid identity. A strict same-content24 PASS plus independent all24 editorial review precedes full100; actual full100 and independent all100 acceptance still precede catalogue metadata publication, generated mirror, cumulative Final, Apple hash adoption and controlled installed acceptance. CatalogueDFAA remains draft/70pending. All24requests/ninegates, HA production configuration, provider/native/physical and user acceptance retain their separate gates.

Current source QA:3649total/3642PASS/7existingSKIP in107.039seconds;Ruff11changedPython0;configuredBandit0medium/high with17existinglow metrics and no newwaiver. Fourteen actual isolatedHA groups preserve265product hashes before/container/after; the separate SDK24 exercise preserves65/65synthetic attempts/responses,4x2original public-input witnesses and12exact structured playback generations. Sixteen causal runtime cases combine15originalrun4 results with the targeted run5 empty-ID assertion correction against identical265product bytes; all original failed assertions remain preserved. The final result-ID guard has separate old-RED/pure-GREEN controls. All owned containers are absent. No network, paid model, installed or native acceptance follows from these tests.

The earlier broad runs remain evidence: the first had five obsolete source-pin assertions; the second had two obsolete264-product-count assertions. Fresh actual receipts were joined to twelve current summaries, with all prior summary bytes and historical v2 fixtures preserved. The exact original100 manifest remainsf6fcebd0349768b83a6824d6dcfeb15e3b229e0c1a168dec4c5a044e1ac43b48; all questions/effects/judges and draft catalogue bytes remain unchanged.
