# Meta Engineering

Meta engineering documents define how humans, AI agents, reviewers and
maintainers collaborate while evolving the DJConnect platform.

## Purpose

The Meta Engineering Foundation defines how DJConnect engineering work is
performed. It does not define product behavior, runtime architecture or
verification expectations. It defines the collaboration, workflow and knowledge
placement model used while evolving those systems.

Use `META_ENGINEERING_INDEX.md` as the canonical navigation page.

## Recommended Reading Order

1. `META_ENGINEERING_INDEX.md`
2. `AI_COLLABORATION_MODEL.md`
3. `REPOSITORY_AS_MEMORY.md`
4. `AI_AGENT_GUIDELINES.md`
5. `ENGINEERING_PLAYBOOK.md`
6. `INNOVATION_ENGINEERING.md`
7. `PHASE_COMPLETION_PROTOCOL.md`
8. `ARCHITECTURAL_HEURISTICS.md`
9. `DECISION_PATTERNS.md`

## Documents

- `AI_COLLABORATION_MODEL.md` defines the canonical AI collaboration model and
  repository-first engineering memory principle.
- `ENGINEERING_PLAYBOOK.md` defines the canonical engineering lifecycle from
  idea to production.
- `INNOVATION_ENGINEERING.md` defines the learning-oriented Innovation
  Engineering mode, including branch, deployment, review and promotion rules.
- `PHASE_COMPLETION_PROTOCOL.md` defines the mandatory completion workflow
  after every implementation phase.
- `ARCHITECTURAL_HEURISTICS.md` defines practical architecture decision-making
  heuristics for the platform.
- `DECISION_PATTERNS.md` defines where newly discovered engineering knowledge
  belongs in the repository.
- `REPOSITORY_AS_MEMORY.md` explains why the repository is the durable
  engineering memory instead of prompts or chat history.
- `AI_AGENT_GUIDELINES.md` defines how AI agents are expected to operate within
  the DJConnect engineering process.

## Relationships

Foundation documents define product direction, platform principles, governance
and ownership. Meta Engineering defines how engineering work preserves and
updates that foundation.

Verification documents define expected behavior and evidence. Meta Engineering
defines the engineering discipline used while creating, qualifying and updating
verification assets.

Technical Design documents implementation reality. Meta Engineering defines how
newly discovered implementation knowledge is classified and placed in the
repository.

The Prompt Library contains execution instructions. Meta Engineering documents
are canonical guidance that prompts reference; prompts must not become the
canonical description of architecture or workflow.

Completion Reports describe phase outcomes. Meta Engineering defines why those
outcomes should become durable repository knowledge.
