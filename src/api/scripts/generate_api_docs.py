"""Generate docs/api.md and docs/openapi.json from the FastAPI app.

Run from the repository root after any API change:
    python src/api/scripts/generate_api_docs.py
"""

# The Markdown template below holds long prose lines on purpose.
# ruff: noqa: E501

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "api"))

from returnright.main import app  # noqa: E402

DOCS_DIR = REPO_ROOT / "docs"

# Endpoints with real behaviour; every other endpoint is a stub that returns 501.
# Add an entry when its story is merged.
IMPLEMENTED = {
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/health/ready"),
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/orders/lookup"),
    ("POST", "/api/v1/returns"),
    ("POST", "/api/v1/returns/{return_code}/photo"),
    ("GET", "/api/v1/returns/{return_code}"),
    ("GET", "/api/v1/returns/{return_code}/timeline"),
    ("GET", "/api/v1/returns/{return_code}/label"),
    ("POST", "/api/v1/returns/{return_code}/ship"),
    ("GET", "/api/v1/warehouse/returns"),
    ("GET", "/api/v1/warehouse/returns/{return_code}"),
    ("POST", "/api/v1/warehouse/returns/{return_code}/receive"),
    ("POST", "/api/v1/warehouse/returns/{return_code}/inspection"),
    ("GET", "/api/v1/finance/approvals"),
    ("POST", "/api/v1/finance/approvals/{return_code}/decision"),
    ("GET", "/api/v1/finance/refunds"),
    ("GET", "/api/v1/finance/refunds/{refund_id}"),
    ("POST", "/api/v1/finance/refunds/{refund_id}/pay"),
    ("GET", "/api/v1/finance/ledger"),
    ("GET", "/api/v1/dashboard"),
    ("GET", "/api/v1/dashboard/return-rates"),
    ("GET", "/api/v1/dashboard/top-reasons"),
    ("GET", "/api/v1/dashboard/flagged-customers"),
    ("GET", "/api/v1/audit"),
    ("GET", "/api/v1/audit/returns/{return_code}"),
}

TAG_ORDER = [
    "health",
    "auth",
    "customer: orders",
    "customer: returns",
    "warehouse",
    "finance",
    "dashboard",
    "audit",
]
TAG_TITLES = {
    "health": "Health",
    "auth": "Auth",
    "customer: orders": "Customer: orders",
    "customer: returns": "Customer: returns",
    "warehouse": "Warehouse",
    "finance": "Finance",
    "dashboard": "Dashboard",
    "audit": "Audit",
}
TAG_ROLES = {
    "auth": "Any staff role",
    "warehouse": "Warehouse agent",
    "finance": "Finance reviewer",
    "dashboard": "Operations manager",
    "audit": "Operations manager",
}

# Sample values for examples, chosen by field name.
SAMPLES: dict[str, Any] = {
    "email": "asha.verma@example.com",
    "order_number": "ORD-104233",
    "return_code": "RR-7K2P9QX4",
    "username": "warehouse1",
    "password": "demo-password",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "product_name": "Cotton kurta",
    "category": "Apparel",
    "name": "Asha Verma",
    "reason": "damaged",
    "reason_details": "Seam torn on arrival",
    "comment": "Photo matches the damage",
    "notes": "Tag attached, light wear",
    "ship_to": "ReturnRight Warehouse, Indore 452010",
    "qr_svg": "<svg ...>",
    "photo_url": "/uploads/RR-7K2P9QX4.jpg",
    "content_type": "image/jpeg",
    "gateway_transaction_id": "gw_9f2c41",
    "approved_by": "finance1",
    "actor": "warehouse1",
    "entity": "return_request",
    "from_status": "in_transit",
    "to_status": "received",
    "note": "Parcel scanned at dock 2",
    "code": "invalid_transition",
    "message": "Return is not in transit",
    "request_id": "3f1c2a9e",
}
DECIMAL_SAMPLES = {
    "amount": "1499.00",
    "unit_price": "1499.00",
    "refund_amount": "1499.00",
    "refund_total": "2998.00",
}
# Response schemas drop the decimal pattern, so money fields are recognised by name.
MONEY_FIELDS = set(DECIMAL_SAMPLES)


# --- schema helpers ------------------------------------------------------------------------------


def ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def anchor(name: str) -> str:
    return "model-" + name.lower().replace("_", "-")


def model_link(name: str) -> str:
    return f"[`{name}`](#{anchor(name)})"


def is_decimal(schema: dict) -> bool:
    return schema.get("type") == "string" and "\\d" in schema.get("pattern", "")


def type_of(schema: dict, field: str = "") -> str:
    """A short, readable type for a JSON schema node."""
    if "$ref" in schema:
        return model_link(ref_name(schema["$ref"]))
    if "anyOf" in schema:
        branches = [b for b in schema["anyOf"] if b.get("type") != "null"]
        numeric = {b.get("type") for b in branches}
        if numeric == {"number", "string"}:
            text = "decimal (string)"
        else:
            text = " \\| ".join(type_of(b, field) for b in branches)
        return text + (" \\| null" if len(branches) < len(schema["anyOf"]) else "")
    kind = schema.get("type")
    if kind == "array":
        return f"list[{type_of(schema.get('items', {}))}]"
    if is_decimal(schema) or (kind == "string" and field in MONEY_FIELDS):
        return "decimal (string)"
    if "contentMediaType" in schema:
        return "file"
    if "enum" in schema:
        return " \\| ".join(f'`"{v}"`' for v in schema["enum"])
    if "const" in schema:
        return f'`"{schema["const"]}"`'
    if kind == "string" and schema.get("format") in ("date", "date-time", "binary"):
        return {"date": "date", "date-time": "datetime", "binary": "file"}[schema["format"]]
    return kind or "any"


def constraints(schema: dict) -> str:
    """Validation rules worth telling a client about."""
    node = schema
    if "anyOf" in schema:
        non_null = [b for b in schema["anyOf"] if b.get("type") != "null"]
        node = non_null[0] if len(non_null) == 1 else {}
    rules = []
    for key, label in (
        ("minLength", "min length"),
        ("maxLength", "max length"),
        ("minItems", "min items"),
        ("maxItems", "max items"),
        ("minimum", "≥"),
        ("exclusiveMinimum", ">"),
        ("maximum", "≤"),
    ):
        if key in node:
            rules.append(f"{label} {node[key]}")
    if "pattern" in node and not is_decimal(node):
        rules.append(f"pattern `{node['pattern']}`")
    if "default" in schema and schema["default"] is not None:
        rules.append(f"default `{json.dumps(schema['default'])}`")
    return ", ".join(rules)


def example(schema: dict, components: dict, field: str = "", depth: int = 0) -> Any:
    """A plausible example value for a schema node."""
    if depth > 6:
        return None
    if "$ref" in schema:
        return example(components[ref_name(schema["$ref"])], components, field, depth + 1)
    if "anyOf" in schema:
        branches = [b for b in schema["anyOf"] if b.get("type") != "null"]
        if {b.get("type") for b in branches} == {"number", "string"}:
            return DECIMAL_SAMPLES.get(field, "1499.00")
        return example(branches[0], components, field, depth + 1) if branches else None
    if "enum" in schema:
        value = SAMPLES.get(field)
        return value if value in schema["enum"] else schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        return {name: example(sub, components, name, depth + 1) for name, sub in props.items()}
    if kind == "array":
        return [example(schema.get("items", {}), components, field, depth + 1)]
    if is_decimal(schema) or (kind == "string" and field in MONEY_FIELDS):
        return DECIMAL_SAMPLES.get(field, "1499.00")
    if kind == "string":
        fmt = schema.get("format")
        if fmt == "date-time":
            return "2026-11-20T10:30:00Z"
        if fmt == "date":
            return "2026-11-20"
        return SAMPLES.get(field, "string")
    if kind == "integer":
        return {"quantity": 1, "page": 1, "size": 20, "total": 1, "expires_in": 3600}.get(field, 1)
    if kind == "number":
        return 0.12 if "rate" in field else 36.5
    if kind == "boolean":
        return field != "customer_flagged"
    return None


def json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```"


# --- markdown sections ---------------------------------------------------------------------------


def access_of(method: str, path: str, op: dict) -> str:
    if not op.get("security"):
        return "Customer (no login)" if op["tags"][0].startswith("customer") else "Public"
    return TAG_ROLES.get(op["tags"][0], "Signed-in staff")


def status_of(method: str, path: str) -> str:
    return "Implemented" if (method, path) in IMPLEMENTED else "Stub: returns 501"


def op_anchor(method: str, path: str) -> str:
    slug = path.strip("/").replace("/", "-").replace("{", "").replace("}", "").replace("_", "-")
    return f"op-{method.lower()}-{slug}"


def operations(spec: dict) -> list[tuple[str, str, dict]]:
    ops = [
        (method.upper(), path, op)
        for path, methods in spec["paths"].items()
        for method, op in methods.items()
    ]
    return sorted(ops, key=lambda o: TAG_ORDER.index(o[2]["tags"][0]))


def render_operation(method: str, path: str, op: dict, components: dict) -> list[str]:
    out = [f'<a id="{op_anchor(method, path)}"></a>', f"### `{method} {path}`", ""]
    out.append(op.get("summary", ""))
    if op.get("description"):
        out += ["", op["description"]]
    out += [
        "",
        f"**Access:** {access_of(method, path, op)} · **Status:** {status_of(method, path)}",
        "",
    ]

    params = op.get("parameters", [])
    if params:
        out += [
            "| Parameter | In | Type | Required | Rules |",
            "| --- | --- | --- | --- | --- |",
        ]
        for p in params:
            schema = p.get("schema", {})
            rules = constraints(schema)
            if p.get("description"):
                rules = f"{p['description']}{'; ' + rules if rules else ''}"
            required = "yes" if p.get("required") else "no"
            out.append(f"| `{p['name']}` | {p['in']} | {type_of(schema)} | {required} | {rules} |")
        out.append("")

    body = op.get("requestBody")
    if body:
        media, content = next(iter(body["content"].items()))
        schema = content["schema"]
        name = ref_name(schema["$ref"]) if "$ref" in schema else ""
        if media == "multipart/form-data":
            fields = components[name]["properties"]
            parts = ", ".join(f"`{f}` ({type_of(s, f)})" for f, s in fields.items())
            out += [f"**Request body:** `multipart/form-data` with {parts}", ""]
        else:
            out += [
                f"**Request body:** {model_link(name)}",
                "",
                json_block(example(schema, components)),
                "",
            ]

    detail = '`{"detail": string}`'
    rows: dict[int, str] = {}
    success_example = None
    for code, resp in op["responses"].items():
        schema = resp.get("content", {}).get("application/json", {}).get("schema")
        body_type = type_of(schema) if schema else detail
        meaning = resp["description"]
        if code.startswith("2"):
            meaning = "Success"
            success_example = example(schema, components) if schema else None
        rows[int(code)] = f"| {code} | {meaning} | {body_type} |"
    if op.get("security"):
        rows[401] = f"| 401 | No or invalid bearer token | {detail} |"
        rows[403] = f"| 403 | Signed in with another role | {detail} |"
    if (method, path) not in IMPLEMENTED:
        rows[501] = f"| 501 | Planned, not implemented yet | {detail} |"
    out += ["| Status | Meaning | Body |", "| --- | --- | --- |"]
    out += [rows[code] for code in sorted(rows)]
    out.append("")

    if success_example is not None:
        out += ["Example response:", "", json_block(success_example), ""]
    return out


def render_models(components: dict) -> list[str]:
    enums = {n: s for n, s in components.items() if "enum" in s}
    objects = {
        n: s
        for n, s in components.items()
        if n not in enums and not n.startswith("Body_") and s.get("type") == "object"
    }

    out = ["## Enums", "", "| Enum | Values |", "| --- | --- |"]
    for name in sorted(enums):
        values = ", ".join(f"`{v}`" for v in enums[name]["enum"])
        out.append(f'| <a id="{anchor(name)}"></a>`{name}` | {values} |')
    out += ["", "## Models", ""]

    for name in sorted(objects):
        schema = objects[name]
        required = set(schema.get("required", []))
        out += [f'<a id="{anchor(name)}"></a>', f"### `{name}`", ""]
        if schema.get("description"):
            out += [schema["description"].strip().splitlines()[0], ""]
        if schema.get("additionalProperties") is False:
            out += ["Unknown fields are rejected.", ""]
        out += ["| Field | Type | Required | Rules |", "| --- | --- | --- | --- |"]
        for field, sub in schema.get("properties", {}).items():
            flag = "yes" if field in required else "no"
            out.append(f"| `{field}` | {type_of(sub, field)} | {flag} | {constraints(sub)} |")
        out.append("")
    return out


INTRO = """# ReturnRight API

The ReturnRight API has {count} endpoints under `/api/v1`, for customers, warehouse agents, finance reviewers and operations managers. {implemented} are implemented; the rest are typed stubs that validate input and return `501` until their story lands.

Generated from the FastAPI app on {today} by `python src/api/scripts/generate_api_docs.py`. Do not edit by hand: change the code, then regenerate. The design behind it is in [api-plan.md](api-plan.md).

## Basics

| Topic | How it works |
| --- | --- |
| Base URL | `http://127.0.0.1:8000/api/v1` locally |
| Interactive docs | `/docs` (Swagger UI), `/redoc`, and the raw schema at `/openapi.json` (copy: [openapi.json](openapi.json)) |
| Staff sign-in | `POST /api/v1/auth/login` returns a JWT. Send it as `Authorization: Bearer <token>`. Each staff route accepts one role |
| Customers | No login. The order number plus email proves ownership. Later calls on a return send the email in `X-Customer-Email`, or in the body for actions |
| Refund idempotency | `POST /finance/refunds/{{refund_id}}/pay` needs an `Idempotency-Key` header. Send the same key on every retry; a refund is never paid twice |
| Pagination | `?page=1&size=20` (size ≤ 100) on list endpoints, returning `items`, `total`, `page`, `size` |
| Money | Decimal strings with two places, in INR, for example `"1499.00"`. Never floats |
| Dates | ISO 8601: `2026-11-20` for dates, `2026-11-20T10:30:00Z` (UTC) for timestamps |
| Request bodies | Strict: unknown fields are rejected with `422`; strings are trimmed |

## Errors

Every error has a JSON body. Today it is FastAPI's `{{"detail": ...}}`; the planned `ErrorResponse` (`code`, `message`, `request_id`) replaces it when the exception handlers land.

| Status | When |
| --- | --- |
| 401 | Staff route without a valid bearer token |
| 403 | Signed in, but with a role this route does not accept |
| 404 | The order or return does not exist, or the email does not match |
| 409 | The return is not in the state this action needs (invalid transition), or the refund is already decided or paid |
| 413 | Uploaded photo is larger than `UPLOAD_MAX_MB` |
| 422 | Input failed validation, or an item is not eligible for return; the body says which field and why |
| 501 | The endpoint is planned but not implemented yet |
| 503 | `/health/ready` only: the database is down |

A `422` validation body looks like this:

```json
{{
  "detail": [
    {{
      "type": "string_pattern_mismatch",
      "loc": ["body", "email"],
      "msg": "String should match pattern '^[^@\\\\s]+@[^@\\\\s]+\\\\.[^@\\\\s]+$'",
      "input": "not-an-email"
    }}
  ]
}}
```

## Endpoints at a glance

| # | Method | Path | What it does | Access | Status |
| --- | --- | --- | --- | --- | --- |
"""


def build() -> str:
    spec = app.openapi()
    components = spec["components"]["schemas"]
    ops = operations(spec)

    lines = [
        INTRO.format(
            count=len(ops),
            implemented=sum((m, p) in IMPLEMENTED for m, p, _ in ops),
            today=date.today().isoformat(),
        ).rstrip("\n")
    ]
    for number, (method, path, op) in enumerate(ops, start=1):
        link = f"[`{path}`](#{op_anchor(method, path)})"
        status = "Done" if (method, path) in IMPLEMENTED else "Stub"
        lines.append(
            f"| {number} | {method} | {link} | {op.get('summary', '')} "
            f"| {access_of(method, path, op)} | {status} |"
        )
    lines.append("")

    current_tag = None
    for method, path, op in ops:
        tag = op["tags"][0]
        if tag != current_tag:
            current_tag = tag
            lines += [f"## {TAG_TITLES.get(tag, tag)}", ""]
        lines += render_operation(method, path, op, components)

    lines += render_models(components)
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "api.md").write_text(build(), encoding="utf-8")
    (DOCS_DIR / "openapi.json").write_text(
        json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {DOCS_DIR / 'api.md'} and {DOCS_DIR / 'openapi.json'}")


if __name__ == "__main__":
    main()
