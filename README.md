# Log Analysis Assistant - Deep Agents Assessment
**Overview:** Extend this starter into an assistant that answers questions about JSON logs (`data/sample_logs.json`: 121 records from 2026-11-03 UTC) and can sustain long conversations. Work independently. If anything is unclear, state your assumption in `ANSWERS.md`.
**Stack:** Python 3.11+, LangChain Deep Agents (`deepagents==0.7.41`), Groq through the assessment’s Cloudflare proxy with GPT-OSS 20B selected in `config/settings.toml` (do not change the provider or model), and JSON log files.

## Setup

Extract the ZIP and open a terminal in `candidate-assessment`. Use Python 3.11 or newer. The ZIP includes the proxy key. Keep it private and leave `config/assessment.env`, the `[model]` settings, and `src/llm.py` as supplied.

### Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main
```

If `py` is unavailable, use `python -m venv .venv` for the first command.

### macOS and Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m src.main
```

Run the first two commands once. In the last command, use `-m src.check_setup` for the live setup check or `-m pytest -q` for offline tests.

## Tasks
1. **Automatic session compaction.** Set the required threshold of **6,000 estimated input tokens** in project configuration. Use only official Deep Agents functionality to compact conversation history automatically when the estimate reaches that threshold.
2. **Log-search tools:** filter by start/end time, log type and log level, combinable in a single call. Return structured, compact results, and handle empty matches and invalid input.
3. **Subagent delegation:** add at least one subagent using the standard Deep Agents API, and have the main agent delegate suitable work to it.

## Expected results (prove each with real run output saved in `evidence/`)
- Compaction fires once the configured threshold is reached, and not before. Changing the setting changes when it fires.
- After compaction the same conversation continues, and earlier facts (e.g. a name and ticket id given in turn 1) are still known.
- Filtered searches return the correct records, and delegation is visible: the subagent ran and used tools.

## Questions (answer briefly in `ANSWERS.md`, citing your evidence)
1. How did you implement compaction, and where does the agent read the 6,000-token threshold?
2. How did you verify that compaction triggered automatically, and what proves the history was actually compacted?
3. How did you verify that important context was preserved after compaction?
4. How do multiple filters combine, and what happens when nothing matches?
5. What does your subagent do compared with the main agent, and how did you verify delegation?
