# Actual returned texts — Dutch pilot, 20 October 2026

Run `nl-v5`: **NO_GO**. These are real isolated HA Assist/model/public-research results with a synthetic music backend and owner. No client, installed speech or audible acceptance.

Full local report: `/private/tmp/djc-contextual-quality-evidence-20261020-approved/contextual-quality-nl-v5.json`.
SHA256: `37575dfa084f5ac7248a421eb39127fa659d437baebd6dbadfc1abf80a6779c7`.

## What the client actually received

### quality-selected-nl

Findings: selected_publication_unavailable:AssertionError.

No published answer.

### quality-band-nl

Findings: generated_answer_missing, closing_question_missing, researched_answer_unqualified, answer_too_sparse_for_requested_story, actual_sources_missing, unexpected_effect_or_concrete_offer.

```text
Ik heb informatie gevonden, maar ik kon dit antwoord nog niet goed genoeg controleren. Probeer je vraag opnieuw.
```

### quality-mood-nl

Findings: mood_feedback_not_published.

No published answer.

## Rejected proposals — never returned as the answer

These were model proposals, not accepted stories. The independent factual reviewer rejected the Nirvana claims; the Mood frame failed before publication.

### quality-band-nl

```text
Nirvana begon als duo: Kurt Cobain zong en speelde gitaar, en Krist Novoselic speelde bas. De band kende verschillende drummers; Dave Grohl kwam er in 1990 bij en bleef het langst. Een mooi inkijkje in hoe Cobain en Novoselic elkaar vonden, zit al vóór de band: Cobains demo met de naam Fecal Matter bewoog Novoselic ertoe om samen met hem een band te beginnen. Op die opname speelde Dale Crover drums en deed hij de achtergrondzang.

En dan dat bijzondere optreden: tijdens MTV Unplugged speelde Nirvana David Bowies “The Man Who Sold the World”. Het werd later opgenomen op het album Unplugged in New York. Mooi hoe zo’n optreden een ander venster op een band biedt, zonder dat het de rauwere oorsprong van hun verhaal uitwist. Welk optreden of nummer van Nirvana zou je verder willen uitlichten?
```

### quality-band-nl

```text
{"supported":false,"unsupported_claims":["Nirvana begon als duo","Cobains demo met de naam Fecal Matter","zonder dat het de rauwere oorsprong van hun verhaal uitwist"]}
```

### mood-feedback-4a63bb79c715efc679f364df80a07476c1650d6fcef79b8b0d34252f4bd6f217

```text
{"frame":"Je feeststemming is bevestigd; voor een concreet muziekvoorstel heb ik alleen nog niet genoeg passende opties. Welke richting spreekt je aan: soul, indie of house? Dat zijn voorkeuren om op af te stemmen, geen gevonden catalogusresultaten: {choices}. De muziek verandert pas als je iets kiest.","genres":["soul","indie","house"]}
```

## Disposition

Keep the evidence gate. Repair the question-angle ranking, unsupported founder/work-title inferences, and misleading genre-choice playback promise. A later rerun must stand on its own actual returned answer and review.

## Rerun `nl-v6` — partial improvement, still NO_GO

Report SHA256: `87d7777dddc7b233555109b7d7597f0b844f11322672820c43cdeed333a8fd47`. Six additional attempts, cumulative10/40; one was cancelled by premature lab Session end.

### quality-selected-nl

Findings: selected_publication_unavailable:AssertionError.

No published answer.

### quality-band-nl

Findings: generated_answer_missing, closing_question_missing, researched_answer_unqualified, answer_too_sparse_for_requested_story, actual_sources_missing.

```text
Ik heb informatie gevonden, maar ik kon dit antwoord nog niet goed genoeg controleren. Probeer je vraag opnieuw.
```

### quality-mood-nl

Findings: none in the mechanical subset.

```text
Een feestelijke stemming, mooi—maar om iets te vinden dat erbij past, heb ik nog een klein duwtje nodig. Welke richting spreekt je aan: house; elektronisch; soul?
```

The Mood clarification is actually persisted and independently model-reviewed. It is one Radio/Party sample, not full Persona/Mood or genre-continuation acceptance. The Nirvana story remains rejected for an unsupported sound/lineup bridge and a claim about original songs absent from the admitted corpus. The fallback is the returned text.

## Rerun `nl-v7` — still NO_GO

Report SHA256: `14d174880723a10e7ae7d12732780174fe63784ddfe8f3d984f8e82655fea53b`. Seven additional completed attempts; cumulative17/40.

### quality-selected-nl

Findings: selected_publication_unavailable:AssertionError.

No published answer.

### quality-band-nl

Findings: generated_answer_missing, closing_question_missing, researched_answer_unqualified, answer_too_sparse_for_requested_story, actual_sources_missing.

```text
Ik heb informatie gevonden, maar ik kon dit antwoord nog niet goed genoeg controleren. Probeer je vraag opnieuw.
```

### quality-mood-nl

Findings: mood_feedback_not_published.

No published answer.

### Rejected proposals and reviews

These are not the replies. The composer review cited an invented full-hash span ID, so its boolean approval was insufficient. Nirvana still includes unsupported repertoire/sonic claims. Mood meaning review returned false; no silent acceptance or fallback generation retry.

**quality-selected-seed**

```text
I like this compact thread: Peter Luts met Barbara Tucker at the International Dance Music Awards in Miami, and they released the single “One.” Peter Luts is credited as a composer of the work behind this recording.
```

**quality-selected-seed**

```text
{"supported":true,"unsupported_claims":[],"review_schema":"source_id_review_v1","claim_checks":[{"text":"I like this compact thread:","kind":"dj_appreciation","evidence_ids":[]},{"text":"Peter Luts met Barbara Tucker at the International Dance Music Awards in Miami, and they released the single “One.”","kind":"relationship","evidence_ids":["6b789d6ff2c8093e:p3"]},{"text":"Peter Luts is credited as a composer of the work behind this recording.","kind":"fact","evidence_ids":["b9883211a83ca98d43bf66b1e4093a3f786f5a4b32ab6a30245995adf6673cf8:0"]}],"language_ok":true,"style_ok":true,"work_focus_preserved":true,"composer_episode_preserved":true}
```

**quality-band-nl**

```text
{"read":"research","reference":"named","exclude_current":false,"subject":"Nirvana","angle":"live_history"}
```

**quality-band-nl**

```text
Nirvana begon bij Kurt Cobain, zanger en gitarist, en bassist Krist Novoselic; de band wisselde daarna meermaals van drummer. Dave Grohl kwam er in 1990 bij en bleef het langst.

Een mooi verhaal zit in hun MTV Unplugged-optreden: tussen de eigen nummers speelde Nirvana ook David Bowies ‘The Man Who Sold the World’. Dat optreden kwam uit op *Unplugged in New York*, een onverwachte, ingetogen tegenhanger van het ruigere beeld waarmee de band vaak wordt verbonden.

Wil je ook horen hoe dat optreden in New York eruitzag, of liever meer over de bandleden?
```

**quality-band-nl**

```text
{"supported":false,"unsupported_claims":["tussen de eigen nummers","een onverwachte, ingetogen tegenhanger van het ruigere beeld waarmee de band vaak wordt verbonden"]}
```

**mood-feedback-745e400c79ab3e325fea862e52fceee04d3cd16d231d109963c7b67482c5906b**

```text
{"frame":"Een feeststemming dus—mooi, daar kan ik mee aan de slag. Voor ik muziek zoek, heb ik nog een klein duwtje nodig: welke richting spreekt je aan, {choices}?","genres":["house","electronic","hip_hop"]}
```

**mood-feedback-745e400c79ab3e325fea862e52fceee04d3cd16d231d109963c7b67482c5906b**

```text
{"language_ok":true,"style_ok":true,"meaning_ok":false}
```


## Rerun `nl-v8` — Mood accepted, stories remain NO_GO

Report SHA256: `4770c172886821ef3391fd84ba366b7e877b78d14d5a8be4767e0a12eb3c394f`. Seven further attempts, cumulative24/40. The frozen source predates the later explicit-null rejection and compacted-source allowed-ID-list correction.

### quality-selected-nl

Findings: selected_publication_unavailable:AssertionError.

No published answer.

### quality-band-nl

Findings: generated_answer_missing, closing_question_missing, researched_answer_unqualified, answer_too_sparse_for_requested_story, actual_sources_missing.

```text
Ik heb informatie gevonden, maar ik kon dit antwoord nog niet goed genoeg controleren. Probeer je vraag opnieuw.
```

### quality-mood-nl

Findings: none in mechanical subset.

```text
Voor een feestelijke draai heb ik nog een beetje richting nodig om muziek te vinden. Waar heb je meer zin in: soul; house; indie?
```

### Rejected proposals — not the replies

The composer reviewer saw an empty allowed-ID list due a compacted-source prompt bug; fixed afterward. The Nirvana reviewer rejects its dated introductory sentence. The existing work-title temporal receipt cannot admit a membership date, even if otherwise literal; this requires a bounded causal repair, not removal of chronology guards.

**quality-selected-seed**

```text
Bij deze opname staat Peter Luts vermeld als componist van het onderliggende werk. Mooi concreet: voor ‘Love Is the Message’ schreef en produceerde hij het nummer, dat het anthem van City Parade werd.
```

**quality-selected-seed**

```text
{"supported":false,"unsupported_claims":["dat het anthem van City Parade werd"],"review_schema":"source_id_review_v1","claim_checks":[{"text":"Bij deze opname staat Peter Luts vermeld als componist van het onderliggende werk.","kind":"fact","evidence_ids":[]},{"text":"Mooi concreet:","kind":"dj_appreciation","evidence_ids":[]},{"text":"voor ‘Love Is the Message’ schreef en produceerde hij het nummer,","kind":"fact","evidence_ids":[]},{"text":"dat het anthem van City Parade werd.","kind":"relationship","evidence_ids":[]}],"language_ok":true,"style_ok":true,"work_focus_preserved":true,"composer_episode_preserved":true}
```

**quality-band-nl**

```text
{"read":"research","reference":"named","exclude_current":false,"subject":"Nirvana","angle":"live_history"}
```

**quality-band-nl**

```text
Nirvana begon met Kurt Cobain en Krist Novoselic; achter het drumstel wisselden verschillende muzikanten elkaar af, tot Dave Grohl in 1990 bij de band kwam en er het langst bleef. Een bijzonder gedocumenteerd optreden is hun *MTV Unplugged*-set: daarin speelde Nirvana ook een cover van David Bowies “The Man Who Sold the World”, te horen op het album *Unplugged in New York*. Een mooi detail: die Bowie-song is niet van Nirvana, maar hun uitvoering werd wel een vastgelegd deel van dat optreden.

Wil je meer horen over die unplugged-uitvoering, of over hoe de bandleden elkaar vonden?
```

**quality-band-nl**

```text
{"supported":false,"unsupported_claims":["Nirvana begon met Kurt Cobain en Krist Novoselic; achter het drumstel wisselden verschillende muzikanten elkaar af, tot Dave Grohl in 1990 bij de band kwam en er het langst bleef."]}
```

**mood-feedback-490f462b20e6fca4c0dc6eb9293255212101a80abf833360ad19313a10d0044a**

```text
{"frame":"Voor een feestelijke draai heb ik nog een beetje richting nodig om muziek te vinden. Waar heb je meer zin in: {choices}?","genres":["soul","house","indie"]}
```

**mood-feedback-490f462b20e6fca4c0dc6eb9293255212101a80abf833360ad19313a10d0044a**

```text
{"language_ok":true,"style_ok":true,"meaning_ok":true,"meaning_reason":"ok"}
```



## Rerun `nl-v9` — still NO_GO

Report SHA256: `422c45ae185505ff9a79b033fcc5b6c2119f84ab7460692487d59912a322baba`. 7 additional attempts; cumulative31/40.

### Actually returned or persisted

**quality-selected-nl** — findings: selected_publication_unavailable:AssertionError.

No published answer captured under response.text; inspect the full report for event fields.

**quality-band-nl** — findings: generated_answer_missing, closing_question_missing, researched_answer_unqualified, answer_too_sparse_for_requested_story, actual_sources_missing.

```text
Ik heb informatie gevonden, maar ik kon dit antwoord nog niet goed genoeg controleren. Probeer je vraag opnieuw.
```

**quality-mood-nl** — findings: none in mechanical subset.

```text
Een feeststemming dus—mooi, daar kan ik alle kanten mee op. Ik heb nog een klein zetje nodig om muziek te zoeken: welke van house; elektronisch; soul spreekt je aan?
```

### Model proposals and reviews — these are not accepted replies

**quality-selected-seed**

```text
Bij de prijs voor “What a Feeling” ontmoette Peter Luts Barbara Tucker; samen brachten ze de single “One” uit. Voor deze opname staat Peter Luts vermeld als componist van het onderliggende werk.
```

**quality-selected-seed**

```text
{"supported":true,"unsupported_claims":[],"language_ok":true,"style_ok":true,"work_focus_preserved":true,"composer_episode_preserved":true,"review_schema":"source_id_review_v1","claim_checks":[{"text":"Bij de prijs voor “What a Feeling” ontmoette Peter Luts Barbara Tucker;","kind":"relationship","evidence_ids":["6b789d6ff2c8093e:p3"]},{"text":" samen brachten ze de single “One” uit.","kind":"relationship","evidence_ids":["6b789d6ff2c8093e:p3"]},{"text":" Voor deze opname staat Peter Luts vermeld als componist van het onderliggende werk.","kind":"fact","evidence_ids":["da65c5b9e11af2ae:0"]}]}
```

**quality-band-nl**

```text
{"read":"research","reference":"named","exclude_current":false,"subject":"Nirvana","angle":"live_history"}
```

**quality-band-nl**

```text
Nirvana begon bij Kurt Cobain, zang en gitaar, en Krist Novoselic, bas; na verschillende drummers kwam Dave Grohl in 1990 bij de band. Bij hun optreden voor *MTV Unplugged* kozen ze voor David Bowies “The Man Who Sold the World”. Dat nummer kreeg zo een plek in een registratie die ook als album verscheen: *Unplugged in New York*.

Wat vind je bijzonder aan die keuze voor Bowie?
```

**quality-band-nl**

```text
{"supported":false,"unsupported_claims":["Nirvana begon bij Kurt Cobain, zang en gitaar, en Krist Novoselic, bas; na verschillende drummers kwam Dave Grohl in 1990 bij de band.","kozen ze voor David Bowies “The Man Who Sold the World”","Dat nummer kreeg zo een plek in een registratie die ook als album verscheen: *Unplugged in New York*."]}
```

**mood-feedback-c069666e51a30d236b32682388aa3021572a9e7b6b4a587ed43029566e49038b**

```text
{"frame":"Een feeststemming dus—mooi, daar kan ik alle kanten mee op. Ik heb nog een klein zetje nodig om muziek te zoeken: welke van {choices} spreekt je aan?","genres":["house","electronic","soul"]}
```

**mood-feedback-c069666e51a30d236b32682388aa3021572a9e7b6b4a587ed43029566e49038b**

```text
{"language_ok":true,"style_ok":true,"meaning_ok":true,"meaning_reason":"ok"}
```

The composer review approved source support, but Core refused its literal-work episode gate. The subsequent unpaid gate replay passes after the bounded title repair; it is not a newly published story. The band review also includes false positives for literal biography material, while the unsourced “unexpected choice” bridge remains a genuine problem. Neither justifies lowering full claim/effect guards.


## Rerun `nl-v10` — still NO_GO

Report SHA256: `eb728c7033ae0180bd0f09329424232e742d246426a42e7294fe7cd88415840b`. 5 additional attempts; cumulative36/40.

### Actually returned or persisted

**quality-selected-nl** — findings: selected_publication_unavailable:AssertionError.

No published answer captured under response.text; inspect the full report for event fields.

**quality-band-nl** — findings: generated_answer_missing, closing_question_missing, researched_answer_unqualified, answer_too_sparse_for_requested_story, actual_sources_missing.

```text
Ik heb informatie gevonden, maar ik kon dit antwoord nog niet goed genoeg controleren. Probeer je vraag opnieuw.
```

### Model proposals and reviews — these are not accepted replies

**quality-selected-seed**

```text
Peter Luts schreef en produceerde ‘Love Is the Message’, het anthem van de City Parade. Een ander spoor in zijn muziekverhaal: op deze opname staat Peter Luts vermeld als componist van het onderliggende werk.
```

**quality-selected-seed**

```text
{"supported":true,"unsupported_claims":[],"language_ok":true,"style_ok":true,"work_focus_preserved":true,"composer_episode_preserved":true,"review_schema":"source_id_review_v1","claim_checks":[{"text":"Peter Luts schreef en produceerde ‘Love Is the Message’, het anthem van de City Parade.","kind":"fact","evidence_ids":["6b789d6ff2c8093e:p2"]},{"text":"Een ander spoor in zijn muziekverhaal:","kind":"dj_appreciation","evidence_ids":[]},{"text":"op deze opname staat Peter Luts vermeld als componist van het onderliggende werk.","kind":"fact","evidence_ids":["da65c5b9e11af2ae:0"]}]}
```

**quality-band-nl**

```text
{"read":"research","reference":"named","exclude_current":false,"subject":"Nirvana","angle":"live_history"}
```

**quality-band-nl**

```text
Nirvana begon met zanger en gitarist Kurt Cobain en bassist Krist Novoselic; na verschillende drummers kwam Dave Grohl in 1990 bij de band. Een bijzonder moment is hun *MTV Unplugged*-optreden, waarop ze ook David Bowies “The Man Who Sold the World” speelden — een onverwachte keuze voor een band die vaak met grunge wordt verbonden. Die uitvoering is te horen op *Unplugged in New York*. Wat spreekt je aan dat optreden het meest aan: de setting of juist de songkeuze?
```

**quality-band-nl**

```text
{"supported":false,"unsupported_claims":["kwam Dave Grohl in 1990 bij de band.","een onverwachte keuze voor een band die vaak met grunge wordt verbonden."]}
```

The composer review approved source support, but Core refused its literal-work episode gate. The subsequent unpaid gate replay passes after the bounded title repair; it is not a newly published story. The band review also includes false positives for literal biography material, while the unsourced “unexpected choice” bridge remains a genuine problem. Neither justifies lowering full claim/effect guards.


## Independent editorial disposition after v10

The composer proposal remains two businesslike fact statements. Its generic
"Een ander spoor" bridge does not establish warmth or a recognizable
Radio/Groove voice. The anthem's original eighth-edition/2005 scope must be
preserved; the generated unqualified event wording was too broad even though
the model reviewer approved it. The proposal was never published. Prompt
clarification and an unpaid work-anchor replay do not change that outcome.
The actual v9 Mood clarification receives editorial GO for this single text;
Persona×Mood variation and a completed genre continuation remain unqualified.
