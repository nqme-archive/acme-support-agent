"""The support agent's tools, declared with Charter."""

import os
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from charter import Body, FromContext, api_key_tool_factory
from charter.packs import stripe as stripe_pack

from billing import owner_of


class Refund(BaseModel):
    charge: Annotated[str, Body()]
    amount: Annotated[Optional[int], Body()] = Field(None, gt=0, le=10_000)
    reason: Annotated[Literal["duplicate", "requested_by_customer"], Body()]
    customer_id: Annotated[str, FromContext()]

    @model_validator(mode="after")
    def their_own_charge(self) -> "Refund":
        if owner_of(self.charge) != self.customer_id:
            raise ValueError("That charge belongs to another customer than this ticket's.")
        return self


stripe = api_key_tool_factory(
    pack="support",
    base_url=os.environ.get("STRIPE_URL", "https://api.stripe.com/"),
    api_key_headers={"Authorization": f"Bearer {os.environ.get('STRIPE_KEY', '')}"},
    body_format="form",
)
refund = stripe(
    name="refund",
    description="Refund one of this ticket's customer's charges.",
    method="POST",
    url_template="v1/refunds",
    args_schema=Refund,
)

TOOLS = [refund, stripe_pack.subscriptions_cancel]
