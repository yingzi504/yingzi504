"""Fixed dictionaries used by JD conversion and the JD library."""

DEPARTMENT_CODES = (
    "CN",
    "TD",
    "TD-E",
    "TD-E1",
    "TD-E2",
    "TD-E3",
    "TD-G",
    "TT",
    "TT-Z",
    "TT-U",
    "TT-U4",
    "TT-U1",
    "TT-U2",
    "TT-U3",
    "TT-E",
    "TT-S",
    "TV",
    "TV-M",
    "TV-M2",
    "TV-M4",
    "TV-M1",
    "TV-M3",
    "TV-F",
    "TV-F2",
    "TV-F1",
    "TV-T",
    "TV-T2",
    "TV-T3",
    "TV-T1",
    "TV-C",
    "TV-A",
    "TV-A1",
    "TV-A3",
    "TV-A2",
    "TV-X",
    "TV-X2",
    "TV-X1",
    "CSO",
    "CSO-V",
    "CSO-N",
    "CSO-E",
    "CSO-S",
    "CSO-C",
    "BA",
    "Admin",
    "Fin",
    "HR",
    "HR2",
    "HR1",
    "IT",
)

DEPARTMENT_CODE_SET = frozenset(DEPARTMENT_CODES)


def validate_department_code(value: str) -> str:
    department = str(value or "").strip()
    if department and department not in DEPARTMENT_CODE_SET:
        raise ValueError("Department must be one of the configured department codes")
    return department
