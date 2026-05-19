from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).parent.parent.parent / "data" / "search.db"


def read_file(filename: str) -> str:
    """Read an SOP document by its ID (e.g., sop-001). Returns the full content."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, title, content FROM documents WHERE id = ? OR id = ?",
        (filename, f"data/{filename}")
    ).fetchone()
    conn.close()
    if row is None:
        return f"Error: Document '{filename}' not found. Available: sop-001 through sop-010."
    return f"# {row['title']}\n\n{row['content']}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "readFile",
            "description": "Read the full content of an SOP document by its ID. Use this to look up detailed procedures, troubleshooting steps, and escalation policies. Call this when you need to read a specific SOP document to answer the user's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The document ID to read, e.g. 'sop-001', 'sop-002', etc."
                    }
                },
                "required": ["filename"]
            }
        }
    }
]
