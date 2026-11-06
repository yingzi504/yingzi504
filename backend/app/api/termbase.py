from fastapi import APIRouter
import json
import os

router = APIRouter()
TERMBASE_FILE = "data/term_base.json"


@router.get("/")
async def get_termbase():
    """获取术语表"""
    if os.path.exists(TERMBASE_FILE):
        with open(TERMBASE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "terms": []}
