import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document
from openai import OpenAI
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


DEFAULT_SYSTEM_PROMPT = """
You are a meeting intelligence assistant.
Return only valid JSON with this exact schema:
{
  "meeting_title": "string",
  "meeting_date": "DD-MM-YYYY",
  "meeting_time": "HH:MM",
  "attendees": ["string"],
  "agenda": ["string"],
  "discussion_points": ["string"],
  "checklist": [
    {
      "task": "string",
      "owner": "string",
      "due_date": "DD-MM-YYYY or TBD",
      "jira_candidate": true
    }
  ],
  "next_meeting_notes": {
    "proposed_agenda": ["string"],
    "carry_forward_items": ["string"]
  },
  "future_innovation_research": ["string"]
}

Rules:
- Do not repeat similar concepts across arrays.
- Ensure checklist items are action-oriented and concrete.
- Infer attendees from transcript/document context when available.
- If a field is unknown, use an empty array or "TBD".
""".strip()


@dataclass
class MeetingRecord:
    meeting_date: str
    meeting_time: str
    title: str
    source_path: Path
    source_text: str


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY environment variable.")
    base_url = os.getenv("OPENAI_BASE_URL")
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)


def parse_filename_metadata(file_name: str) -> tuple[str, str, str]:
    stem = Path(file_name).stem
    parts = [p.strip() for p in stem.split(",")]
    if len(parts) >= 3:
        return parts[0], parts[1], ",".join(parts[2:]).replace(" ", "")
    now = datetime.now()
    return now.strftime("%d-%m-%Y"), now.strftime("%H:%M"), stem.replace(" ", "")


def read_source_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        doc = Document(str(path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported file extension: {path.suffix}")


def collect_inputs(input_dir: Path) -> list[MeetingRecord]:
    supported = {".txt", ".md", ".docx", ".pdf"}
    records: list[MeetingRecord] = []
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in supported:
            date_str, time_str, title = parse_filename_metadata(path.name)
            records.append(
                MeetingRecord(
                    meeting_date=date_str,
                    meeting_time=time_str,
                    title=title,
                    source_path=path,
                    source_text=read_source_file(path),
                )
            )
    return records


def summarize_record(client: OpenAI, model: str, record: MeetingRecord) -> dict[str, Any]:
    user_prompt = f"""
Meeting metadata:
- date: {record.meeting_date}
- time: {record.meeting_time}
- title: {record.title}
- source_file: {record.source_path.name}

Meeting content:
{record.source_text}
""".strip()

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    parsed["source_file"] = record.source_path.name
    return parsed


def render_txt(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Meeting Title: {summary.get('meeting_title', 'TBD')}")
    lines.append(f"Date: {summary.get('meeting_date', 'TBD')}")
    lines.append(f"Time: {summary.get('meeting_time', 'TBD')}")
    lines.append(f"Source File: {summary.get('source_file', 'TBD')}")
    lines.append("")

    def add_section(title: str, items: list[str]) -> None:
        lines.append(f"{title}:")
        if not items:
            lines.append("- None")
        else:
            for item in items:
                lines.append(f"- {item}")
        lines.append("")

    add_section("Attendees", summary.get("attendees", []))
    add_section("Agenda", summary.get("agenda", []))
    add_section("Discussion Points", summary.get("discussion_points", []))

    lines.append("Checklist:")
    checklist = summary.get("checklist", [])
    if not checklist:
        lines.append("- None")
    else:
        for item in checklist:
            jira_flag = "Yes" if item.get("jira_candidate") else "No"
            lines.append(
                f"- Task: {item.get('task', 'TBD')} | Owner: {item.get('owner', 'TBD')} | "
                f"Due: {item.get('due_date', 'TBD')} | Jira Candidate: {jira_flag}"
            )
    lines.append("")

    next_notes = summary.get("next_meeting_notes", {})
    add_section("Next Meeting Proposed Agenda", next_notes.get("proposed_agenda", []))
    add_section("Carry Forward Items", next_notes.get("carry_forward_items", []))
    add_section("Future Innovation Research", summary.get("future_innovation_research", []))

    return "\n".join(lines).strip() + "\n"


def write_pdf(text_content: str, output_pdf_path: Path) -> None:
    c = canvas.Canvas(str(output_pdf_path), pagesize=A4)
    width, height = A4
    x = 15 * mm
    y = height - 15 * mm
    max_width = width - 30 * mm
    line_height = 6 * mm

    for raw_line in text_content.splitlines():
        line = raw_line if raw_line else " "
        wrapped = wrap_text(line, c, max_width)
        for chunk in wrapped:
            if y < 20 * mm:
                c.showPage()
                y = height - 15 * mm
            c.drawString(x, y, chunk)
            y -= line_height
    c.save()


def wrap_text(text: str, c: canvas.Canvas, max_width: float) -> list[str]:
    words = text.split(" ")
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", value)
    return cleaned or "Meeting"


def output_filename(summary: dict[str, Any]) -> str:
    date_str = summary.get("meeting_date", "TBD")
    time_str = summary.get("meeting_time", "TBD").replace(":", "-")
    title = safe_slug(summary.get("meeting_title", "Meeting"))
    return f"{date_str},{time_str},{title}"


def run_pipeline(input_dir: Path, output_dir: Path, model: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = collect_inputs(input_dir)
    if not records:
        raise FileNotFoundError(f"No supported input files found in: {input_dir}")

    client = get_client()
    for record in records:
        summary = summarize_record(client, model, record)
        base = output_filename(summary)
        txt_path = output_dir / f"{base}.txt"
        pdf_path = output_dir / f"{base}.pdf"

        txt_data = render_txt(summary)
        txt_path.write_text(txt_data, encoding="utf-8")
        write_pdf(txt_data, pdf_path)
        print(f"Generated: {txt_path.name} and {pdf_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Meeting notes summarization pipeline")
    parser.add_argument("--input-dir", default="meeting_app/input_docs", help="Input docs folder")
    parser.add_argument("--output-dir", default="meeting_app/output_docs", help="Output docs folder")
    parser.add_argument("--model", default=os.getenv("MEETING_MODEL", "gpt-4o-mini"), help="LLM model name")
    args = parser.parse_args()

    run_pipeline(Path(args.input_dir), Path(args.output_dir), args.model)


if __name__ == "__main__":
    main()