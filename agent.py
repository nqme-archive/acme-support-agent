"""The support agent: a ticket, whose ticket it is, and the tools."""

import os

from openai import AsyncOpenAI

from charter import ToolSession
from charter.adapters.openai import run

from tools import TOOLS

llm = AsyncOpenAI(api_key=os.environ["FIREWORKS_API_KEY"], base_url="https://api.fireworks.ai/inference/v1")
MODEL = "accounts/fireworks/models/glm-5p3-flash"
SYSTEM = (
    "You are the support agent for Acme Cloud. You are helping the customer who opened this ticket. "
    "Use your tools to act. Keep replies short."
)


async def answer(ticket):
    return await run(
        llm,
        model=MODEL,
        session=ToolSession(TOOLS, progressive=False),
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": ticket.message},
        ],
        context={"customer_id": ticket.customer},
        temperature=0,
    )
