import os
import json
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
from backend.phase3.tools import TOOLS, read_file
from backend.phase3.prompts import SYSTEM_PROMPT
from backend.phase2.vector_store import VectorStore


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def agent_chat(message: str) -> AsyncGenerator[str, None]:
    """Main agent loop, yields SSE event strings."""
    try:
        async for event in _agent_chat_impl(message):
            yield event
    except Exception as e:
        logging.exception("Agent loop error")
        yield sse({"type": "text", "content": f"\n\nAgent 处理出错: {str(e)}\n请重试或检查 API 配置。"})
        yield sse({"type": "done"})


async def _agent_chat_impl(message: str) -> AsyncGenerator[str, None]:
    client = get_client()

    if client is None:
        yield sse({"type": "text", "content": "Agent 正在检索相关 SOP 文档...\n\n"})
        vs = VectorStore()
        results = vs.hybrid_search(message, limit=3)
        if results:
            yield sse({"type": "text", "content": f"找到 {len(results)} 个相关文档，正在读取...\n\n"})
            for r in results:
                yield sse({"type": "tool", "file": r["id"]})
                content = read_file(r["id"])
                yield sse({"type": "text", "content": f"## {r['title']} ({r['id']})\n\n{content[:1000]}\n\n---\n\n"})
            yield sse({"type": "text", "content": "**建议**: 请根据以上 SOP 文档内容进行故障排查。如需更精确的 AI 分析，请配置 OPENAI_API_KEY 环境变量。"})
        else:
            yield sse({"type": "text", "content": "未找到相关 SOP 文档。请尝试其他关键词。"})
        yield sse({"type": "done"})
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message}
    ]

    yield sse({"type": "text", "content": "Agent 正在分析问题...\n\n"})

    for iteration in range(5):
        stream = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            stream=True
        )

        tool_calls = []
        content_buffer = ""

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                content_buffer += delta.content
                yield sse({"type": "text", "content": delta.content})

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if hasattr(tc, 'index') else 0
                    while len(tool_calls) <= idx:
                        tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.type:
                        tool_calls[idx]["type"] = tc.type
                    if tc.function:
                        if tc.function.name:
                            tool_calls[idx]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls[idx]["function"]["arguments"] += tc.function.arguments

        if not tool_calls or not any(tc["function"]["name"] for tc in tool_calls):
            yield sse({"type": "done"})
            return

        messages.append({"role": "assistant", "content": content_buffer or None, "tool_calls": tool_calls})

        for tc in tool_calls:
            name = tc["function"]["name"]
            if name == "readFile":
                try:
                    args = json.loads(tc["function"]["arguments"])
                    filename = args.get("filename", "")
                except json.JSONDecodeError:
                    filename = ""
                if filename:
                    yield sse({"type": "tool", "file": filename})
                result = read_file(filename) if filename else "Error: no filename provided"
            else:
                result = f"Unknown tool: {name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

    yield sse({"type": "text", "content": "\n\n分析完成，生成最终回答...\n\n"})
    stream = await client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
        messages=messages,
        stream=True
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield sse({"type": "text", "content": delta.content})

    yield sse({"type": "done"})


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
