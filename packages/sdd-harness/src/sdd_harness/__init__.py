"""Engines behind the intake, route and refine skills.

The package is deliberately split so every engine runs offline and deterministically
inside a Claude Code session (where the host model does the reasoning), and gains
Claude-backed nodes when it runs as a LangGraph service with an API credential.

- ``sdd_harness.rag``       hybrid lexical + dense retrieval with provenance and staleness checks
- ``sdd_harness.reasoning`` durable decision traces and visible reasoning chains
- ``sdd_harness.intake``    intake files, sufficiency rows, question cards and the session graph
- ``sdd_harness.router``    the skill catalog graph, classification and security screen
- ``sdd_harness.ledger``    the per-phase decision ledger for refinement
"""

__version__ = "0.1.0"
