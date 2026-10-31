"""Run the agent on one ticket, against a local stand-in for Stripe that counts what reaches it."""

import asyncio
import json
import os
import shutil
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

received = []


class StandInStripe(BaseHTTPRequestHandler):
    def do_POST(self):
        received.append(self.path)
        body = json.dumps({"id": "re_1", "object": "refund", "status": "succeeded"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), StandInStripe)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ["STRIPE_URL"] = f"http://127.0.0.1:{server.server_port}/"
os.environ["STRIPE_KEY"] = "rk_test_standin"

from agent import answer  # noqa: E402  (after the stand-in, so the tools point at it)

TICKET = SimpleNamespace(customer="cus_42", message="Hi, I was charged ch_2 for a Team plan I never ordered. Can you refund it?")
COLOURS = {"customer": "\033[38;5;111m", "model": "\033[38;5;183m", "charter": "\033[38;5;210m"}
WIDTH = min(shutil.get_terminal_size().columns, 110) - 12


def say(who, text):
    lines = [w for para in text.strip().split("\n") for w in (textwrap.wrap(para, WIDTH) or [""])]
    colour = COLOURS[who]
    print(f"{colour}{who:<10}\033[0m{colour if who == 'charter' else ''}{lines[0]}\033[0m")
    for line in lines[1:]:
        print(f"{'':<10}{colour if who == 'charter' else ''}{line}\033[0m")


print(f"\033[2mticket from {TICKET.customer} · glm-5p3-flash on Fireworks\033[0m\n")
say("customer", TICKET.message)
result = asyncio.run(answer(TICKET))
for m in result.messages[2:]:
    m = m if isinstance(m, dict) else m.model_dump()
    for call in m.get("tool_calls") or []:
        args = ", ".join(f'{k}="{v}"' for k, v in json.loads(call["function"]["arguments"]).items())
        say("model", f"{call['function']['name']}({args})")
    if m["role"] == "tool":
        content = m.get("content") or ""
        say("charter", "refused: " + content.split("Value error, ")[-1] if "Value error" in content else content)
    elif m["role"] == "assistant" and m.get("content"):
        say("model", m["content"].replace("**", ""))
print(f"\n\033[2mrequests that reached Stripe: {len(received)}\033[0m")
