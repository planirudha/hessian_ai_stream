# Meeting Notes App

This app ingests meeting content (`.txt`, `.md`, `.docx`, `.pdf`), summarizes it with an LLM, and stores structured outputs as both `.txt` and `.pdf`.

## Current pipeline

1. **Input ingestion** from `meeting_app/input_docs`
2. **Metadata parsing** from filename pattern:
   - `DD-MM-YYYY,HH:MM,Title.ext`
3. **LLM summarization** into:
   - Meeting date/time/title
   - Attendees
   - Agenda
   - Discussion points
   - Checklist with owner, due date, Jira candidate flag
   - Next meeting proposed agenda
   - Future innovation/research ideas
4. **Output generation** to `meeting_app/output_docs`:
   - `DD-MM-YYYY,HH-MM,Title.txt`
   - `DD-MM-YYYY,HH-MM,Title.pdf`

## Run

Set environment variables:

- `OPENAI_API_KEY` (required)
- `OPENAI_BASE_URL` (optional, for custom/enterprise endpoint)
- `MEETING_MODEL` (optional, defaults to `gpt-4o-mini`)

Install dependencies:

```bash
pip install -r requirements.txt
```

Run pipeline:

```bash
python meeting_app/main.py --input-dir meeting_app/input_docs --output-dir meeting_app/output_docs
```

## Plugin and integration plan

- **Zoom / Google Meet plugin layer**
  - Adapter interface: `extract_text(source) -> transcript_text`
  - First implementation: file-based ingestion (already done)
  - Next implementation: real-time transcript stream adapters

- **Jira integration (later phase)**
  - Filter checklist where `jira_candidate == true`
  - Add approval step
  - Create Jira ticket drafts automatically

- **USPs roadmap**
  - Next meeting agenda generator from carry-forward items
  - Personalized task distribution assistant
  - Long-term memory for innovation/process research trends
