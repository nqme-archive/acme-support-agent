"""Acme's own database. Here: who owns each charge."""

CHARGES = {"ch_1": "cus_42", "ch_1b": "cus_42", "ch_2": "cus_7"}


def owner_of(charge: str) -> str:
    return CHARGES.get(charge, "")
