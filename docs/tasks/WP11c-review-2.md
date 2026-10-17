<review>
Reviewer (Claude Code) ran a live departure question through /api/ask (15.5 s, 6 tools, varied follow-ups). Two small
fixes remain.
</review>

<fixes>
1. Pronouns. The live answer said "Removing him cuts the main collaboration group…" about a real contributor; the model
   inferred a pronoun from a name. Add one sentence to the static system prompt (src/busfactor/agent/prompt.py): refer
   to people by name or GitHub login, never infer pronouns from a name, and use "they" if a pronoun is needed. Keep the
   prompt otherwise unchanged and static (prompt caching). Add a unit test that the prompt contains this rule.
2. The ask_timing log lines (src/busfactor/agent/loop.py, LOGGER = logging.getLogger(__name__)) never reach the server
   output: under uvicorn the `busfactor` logger has no handler. In src/busfactor/api/app.py (or __main__), attach a
   StreamHandler with a simple "%(levelname)s %(name)s %(message)s" format to the `busfactor` logger once at startup
   (no duplicate handlers on reload, propagate=False). Add a test with caplog or a handler check.
</fixes>

<verification_loop>
pytest must pass.
</verification_loop>

<compact_output_contract>
One line per fix; pytest summary.
</compact_output_contract>
