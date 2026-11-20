"""Enum member names must equal the codes the database accepts (db/schema_v2.sql)."""

import re
from pathlib import Path

import pytest

from returnright.domain.enums import (
    Grade,
    ItemDecision,
    LedgerEntryType,
    RefundMethod,
    RefundStatus,
    ReturnReason,
    ReturnStatus,
    Role,
)

SCHEMA = (Path(__file__).resolve().parents[3] / "db" / "schema_v2.sql").read_text(encoding="utf-8")
CHECK_LISTS = [
    {code.strip().strip("'") for code in values.split(",")}
    for values in re.findall(r"CHECK \(\w+ IN \(([^)]*)\)\)", SCHEMA)
]
REASON_INSERT = SCHEMA.split("INSERT INTO return_reasons", 1)[1].split(";", 1)[0]
REASON_CODES = set(re.findall(r"\('([A-Z_]+)',", REASON_INSERT))


@pytest.mark.parametrize(
    "enum",
    [ReturnStatus, Grade, ItemDecision, RefundMethod, RefundStatus, Role, LedgerEntryType],
)
def test_enum_names_match_a_database_check_list(enum):
    assert {member.name for member in enum} in CHECK_LISTS


def test_return_reason_names_match_the_seeded_reason_codes():
    assert {member.name for member in ReturnReason} == REASON_CODES
