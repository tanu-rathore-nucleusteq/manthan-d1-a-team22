"""Generates short, unguessable return codes for labels and QR codes."""

import secrets

# No 0, O, 1 or I, so a code read aloud or typed from a label is unambiguous.
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LENGTH = 8


def new_return_code() -> str:
    """RR- plus 8 random characters, about 10^12 possibilities, for example RR-7K2P9QX4."""
    return "RR-" + "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
