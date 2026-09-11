from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

CATEGORY_ALIASES = {
    "OPEN": "OPEN",
    "GENERAL": "OPEN",
    "GEN": "OPEN",
    "OBC NCL": "OBC_NCL",
    "OBC-NCL": "OBC_NCL",
    "OTHER BACKWARD CLASSES - NON CREAMY LAYER": "OBC_NCL",
    "SC": "SC",
    "ST": "ST",
    "EWS": "EWS",
    "GEN-EWS": "EWS",
    "OPEN-PWD": "OPEN_PWD",
    "OPEN (PWD)": "OPEN_PWD",
    "OBC-NCL-PWD": "OBC_NCL_PWD",
    "OBC-NCL (PWD)": "OBC_NCL_PWD",
    "SC-PWD": "SC_PWD",
    "SC (PWD)": "SC_PWD",
    "ST-PWD": "ST_PWD",
    "ST (PWD)": "ST_PWD",
    "EWS-PWD": "EWS_PWD",
    "GEN-EWS-PWD": "EWS_PWD",
    "GEN-EWS (PWD)": "EWS_PWD",
}
QUOTA_ALIASES = {
    "AI": "ALL_INDIA",
    "ALL INDIA": "ALL_INDIA",
    "ALL-INDIA": "ALL_INDIA",
    "HS": "HOME_STATE",
    "HOME STATE": "HOME_STATE",
    "OS": "OTHER_STATE",
    "OTHER STATE": "OTHER_STATE",
    "OPEN SEAT QUOTA": "ALL_INDIA",
    "ALL INDIA EXCEPT CENTRAL UNIVERSITY": "ALL_INDIA",
    # JoSAA uses domicile-state abbreviations for a small set of state-specific
    # quotas (for example GO for Goa and JK for Jammu & Kashmir).  Canonical
    # eligibility models these as the home-state quota.
    "GO": "HOME_STATE",
    "JK": "HOME_STATE",
    "LA": "HOME_STATE",
    "SELF FINANCED MERIT SEAT": "ALL_INDIA",
    "SELF_FINANCED_MERIT_SEAT": "ALL_INDIA",
    "INTERNAL PUDUCHERRY UT DOMICILE": "HOME_STATE",
    "INTERNAL_PUDUCHERRY_UT_DOMICILE": "HOME_STATE",
}
GENDER_ALIASES = {
    "GENDER-NEUTRAL": "GENDER_NEUTRAL",
    "GENDER NEUTRAL": "GENDER_NEUTRAL",
    "NEUTRAL": "GENDER_NEUTRAL",
    "FEMALE-ONLY (INCLUDING SUPERnumerary)".upper(): "FEMALE_ONLY",
    "FEMALE ONLY": "FEMALE_ONLY",
}
STATE_ALIASES = {
    "ANDAMAN & NICOBAR ISLANDS": "AN",
    "ANDAMAN AND NICOBAR ISLANDS": "AN",
    "ANDHRA PRADESH": "AP",
    "ARUNACHAL PRADESH": "AR",
    "ASSAM": "AS",
    "BIHAR": "BR",
    "CHANDIGARH": "CH",
    "CHHATTISGARH": "CG",
    "CHATTISGARH": "CG",
    "DADRA AND NAGAR HAVELI": "DN",
    "DELHI (NCT)": "DL",
    "DELHI": "DL",
    "MAHARASHTRA": "MH",
    "RAJASTHAN": "RJ",
    "KARNATAKA": "KA",
    "TAMIL NADU": "TN",
    "UTTAR PRADESH": "UP",
    "GOA": "GA",
    "GUJARAT": "GJ",
    "HARYANA": "HR",
    "HIMACHAL PRADESH": "HP",
    "JAMMU AND KASHMIR": "JK",
    "JAMMU & KASHMIR": "JK",
    "JHARKHAND": "JH",
    "KERALA": "KL",
    "LADAKH": "LA",
    "MADHYA PRADESH": "MP",
    "MANIPUR": "MN",
    "MEGHALAYA": "ML",
    "MIZORAM": "MZ",
    "NAGALAND": "NL",
    "ODISHA": "OD",
    "ORISSA": "OD",
    "PUDUCHERRY": "PY",
    "PUNJAB": "PB",
    "SIKKIM": "SK",
    "TELANGANA": "TS",
    "TRIPURA": "TR",
    "UTTARAKHAND": "UK",
    "WEST BENGAL": "WB",
}


def normalize_token(value: Any) -> str:
    text = str(value or "").strip().upper()
    return re.sub(r"[^A-Z0-9]+", "_", text).strip("_")


def normalize_category(value: Any) -> str:
    text = " ".join(str(value or "").strip().upper().split())
    return CATEGORY_ALIASES.get(text, normalize_token(text))


def normalize_quota(value: Any) -> str:
    text = " ".join(str(value or "").strip().upper().split())
    return QUOTA_ALIASES.get(text, normalize_token(text))


def normalize_gender_pool(value: Any) -> str:
    text = " ".join(str(value or "").strip().upper().split())
    return GENDER_ALIASES.get(text, normalize_token(text))


def normalize_state(value: Any) -> str:
    text = " ".join(str(value or "").strip().upper().split())
    if len(text) == 2:
        return text
    return STATE_ALIASES.get(text, normalize_token(text))


def normalize_integer(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not an integer")
    return int(str(value).replace(",", "").strip())


def normalize_decimal(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal value: {value}") from exc


def normalize_date(value: Any) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def normalize_admission_record(values: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: value.strip() if isinstance(value, str) else value for key, value in values.items()
    }
    result.update(
        academic_year=normalize_integer(values.get("academic_year")),
        round_sequence=normalize_integer(values.get("round_sequence")),
        category_code=normalize_category(values.get("category")),
        quota_code=normalize_quota(values.get("quota")),
        gender_pool_code=normalize_gender_pool(values.get("gender_pool")),
        state_code=normalize_state(values.get("state")),
        opening_rank=normalize_integer(values.get("opening_rank")),
        closing_rank=normalize_integer(values.get("closing_rank")),
        seat_count=normalize_integer(values.get("seat_count", 0)),
    )
    return result


def normalize_scholarship_record(values: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: value.strip() if isinstance(value, str) else value for key, value in values.items()
    }
    result.update(
        academic_year=normalize_integer(values.get("academic_year")),
        provider_type=normalize_token(values.get("provider_type")),
        status=normalize_token(values.get("status", "PUBLISHED")),
        income_max=normalize_decimal(values.get("income_max")),
        minimum_marks=normalize_decimal(values.get("minimum_marks")),
        benefit_amount=normalize_decimal(values.get("benefit_amount")),
        application_start_date=normalize_date(values.get("application_start_date")),
        deadline=normalize_date(values.get("deadline")),
    )
    return result
