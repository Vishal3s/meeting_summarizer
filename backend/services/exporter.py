import json
from typing import Dict, Any

class MeetingExporter:
    """Exports meeting data into various document formats."""

    @staticmethod
    def to_markdown(meeting_dict: Dict[str, Any]) -> str:
        title = meeting_dict.get("title", "Meeting Summary")
        date_str = meeting_dict.get("created_at", "N/A")
        duration = meeting_dict.get("duration_seconds", 0.0)
        summary = meeting_dict.get("summary", "N/A")
        decisions = meeting_dict.get("key_decisions", [])
        action_items = meeting_dict.get("action_items", [])
        topics = meeting_dict.get("topics", [])
        transcript = meeting_dict.get("transcript", "")
        asr_prov = meeting_dict.get("asr_provider_used", "N/A")
        llm_prov = meeting_dict.get("llm_provider_used", "N/A")

        md = []
        md.append(f"# {title}")
        md.append(f"**Date:** {date_str} | **Duration:** {duration}s | **ASR:** {asr_prov} | **LLM:** {llm_prov}")
        md.append("\n---\n")

        md.append("## Executive Summary")
        md.append(summary)
        md.append("\n")

        if decisions:
            md.append("## Key Decisions")
            for d in decisions:
                md.append(f"- {d}")
            md.append("\n")

        if action_items:
            md.append("## Action Items")
            for item in action_items:
                status_icon = "[x]" if item.get("status") == "Done" else "[ ]"
                assignee = item.get("assignee", "Unassigned")
                priority = item.get("priority", "Medium")
                task = item.get("task", "")
                md.append(f"- {status_icon} **{task}** (Assignee: {assignee} | Priority: {priority})")
            md.append("\n")

        if topics:
            md.append("## Main Discussion Topics")
            for t in topics:
                t_title = t.get("topic", "Topic")
                t_sum = t.get("summary", "")
                md.append(f"### {t_title}")
                md.append(t_sum)
            md.append("\n")

        if transcript:
            md.append("## Full Transcript")
            md.append("```text")
            md.append(transcript)
            md.append("```")

        return "\n".join(md)

    @staticmethod
    def to_json(meeting_dict: Dict[str, Any]) -> str:
        return json.dumps(meeting_dict, indent=2)

    @staticmethod
    def to_text(meeting_dict: Dict[str, Any]) -> str:
        title = meeting_dict.get("title", "Meeting Summary")
        summary = meeting_dict.get("summary", "")
        decisions = meeting_dict.get("key_decisions", [])
        action_items = meeting_dict.get("action_items", [])
        transcript = meeting_dict.get("transcript", "")
        
        txt = [f"=== {title.upper()} ===", "\n[SUMMARY]", summary, "\n[KEY DECISIONS]"]
        for d in decisions:
            txt.append(f"• {d}")
        txt.append("\n[ACTION ITEMS]")
        for a in action_items:
            txt.append(f"• [{a.get('status', 'To Do')}] {a.get('task')} (Assignee: {a.get('assignee')})")
        if transcript:
            txt.append("\n[FULL TRANSCRIPT]")
            txt.append(transcript)
        return "\n".join(txt)
