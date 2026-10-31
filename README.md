# Acme support agent

A support agent whose refund tool is declared with [Charter](https://github.com/r28ai/charter). Made for Charter's demo
video: Acme Cloud is made up, and `ticket.py` runs against a local stand-in for Stripe that counts what reaches it.

- `tools.py`: the refund tool. The model fills in the charge; Acme's app says whose ticket it is (`FromContext`); the
  rule refuses a charge that belongs to another customer, before anything is sent.
- `ticket.py`: one ticket, live, on glm-5p3-flash (needs `FIREWORKS_API_KEY`).
- `review.py`: what the agent can reach, printed from the same declarations.
- `check_egress.py`: the CI check. It fails a pull request that widens what the agent can reach until `egress.json` is
  updated and reviewed.
- `connect.py`: each customer connects their own GitHub; the agent acts as them (needs a GitHub OAuth App).
