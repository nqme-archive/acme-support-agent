"""Each Acme customer connects their own GitHub; the agent then acts as them, with their token, in Acme's database."""

import os
import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from charter.auth import OAuth2Flow, OAuth2Server, Revocation, StaticTokenProvider, SubjectProvider, revoke_token
from charter.auth import scopes_for, states_match, use_subject
from charter.packs import github

GITHUB = OAuth2Server(
    issuer="https://github.com",
    authorization_endpoint="https://github.com/login/oauth/authorize",
    token_endpoint="https://github.com/login/oauth/access_token",
    token_endpoint_auth_method="client_secret_post",
    revocation=Revocation(
        "https://api.github.com/applications/{client_id}/grant",
        token_type="access_token",
        auth_method="client_secret_basic",
        token_field="access_token",
        http_method="DELETE",
        request_format="json",
        gone_statuses=(404, 422),
    ),
)
CLIENT = {"client_id": os.environ["GITHUB_CLIENT_ID"], "client_secret": os.environ["GITHUB_CLIENT_SECRET"]}
flow = OAuth2Flow(GITHUB, **CLIENT, redirect_uri="http://localhost:8000/callback")

db = sqlite3.connect("grants.db", check_same_thread=False)  # Acme's database: one token per customer
db.execute("create table if not exists grants (user text primary key, token text)")


def token_of(user):
    row = db.execute("select token from grants where user = ?", (user,)).fetchone()
    return row and row[0]


users = SubjectProvider(lambda user: StaticTokenProvider(token_of(user) or ""))
github.configure(credential_provider=users)
app = FastAPI()

PAGE = """<!doctype html><meta charset=utf-8><title>Acme Support</title>
<style>body{{font:18px/1.5 -apple-system,system-ui,sans-serif;background:#f6f7f9;color:#14151a;margin:0}}
main{{max-width:560px;margin:14vh auto;background:#fff;border:1px solid #e3e5ea;border-radius:14px;padding:40px 44px}}
h1{{font-size:26px;margin:0 0 6px}} p{{color:#555b66;margin:0 0 26px}} small{{color:#8a909b}}
a.b{{display:inline-block;background:#14151a;color:#fff;text-decoration:none;padding:12px 20px;border-radius:9px}}</style>
<main><h1>Acme Support</h1>{body}</main>"""


@app.get("/")
async def home(user: str):
    if not token_of(user):
        body = (f"<p>Let Acme's support agent look into your GitHub when you open a ticket.</p>"
                f'<a class=b href="/connect?user={user}">Connect GitHub</a>')
        return HTMLResponse(PAGE.format(body=body))
    with use_subject(user):  # every call from here runs with this customer's own token
        me = await github.users_get_authenticated.ainvoke({})
    body = (f"<p>Connected as <b>{me['login']}</b>. The agent now acts in your GitHub as you, "
            f"with your token, stored in Acme's own database.</p><small>{me.get('public_repos', 0)} public repos</small>")
    return HTMLResponse(PAGE.format(body=body))


@app.get("/connect")
def connect(user: str):
    request = flow.authorize(scopes_for([github.users_get_authenticated]))
    response = RedirectResponse(request.url)
    response.set_cookie("oauth", f"{request.state}:{request.code_verifier}:{user}", httponly=True)
    return response


@app.get("/callback")
async def callback(request: Request, code: str, state: str):
    expected, verifier, user = request.cookies["oauth"].split(":", 2)
    if not states_match(expected, state):
        return HTMLResponse("That link wasn't started here.", status_code=400)
    grant = await flow.exchange(code, code_verifier=verifier, expect_refresh_token=False)
    db.execute("insert or replace into grants values (?, ?)", (user, grant.access_token))
    db.commit()
    return RedirectResponse(f"/?user={user}")


@app.get("/disconnect")
async def disconnect(user: str):
    await revoke_token(GITHUB, access_token=token_of(user), **CLIENT)  # ends it at GitHub too
    db.execute("delete from grants where user = ?", (user,))
    db.commit()
    users.forget(user)
    return RedirectResponse(f"/?user={user}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
