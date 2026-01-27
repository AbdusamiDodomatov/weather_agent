import os
import json
import httpx
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import RootModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

router = APIRouter()

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

# --- Models ---
class WebhookRequest(RootModel):
    root: Dict[str, Any]

# --- Helpers ---
async def get_usd_rate() -> float:
    """Fetches the current USD to UZS exchange rate from CBU API."""
    url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            # Find USD
            for item in data:
                if item.get("Ccy") == "USD":
                    return float(item.get("Rate", 0))
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
    return 12850.0  # Fallback rate

# --- Core Logic ---
@router.post("/webhook/uy-joy")
async def handle_uy_joy(payload: WebhookRequest):
    raw_payload = payload.root
    
    if isinstance(raw_payload, list):
        body = raw_payload[0] if raw_payload else {}
    else:
        body = raw_payload.get("body") if isinstance(raw_payload.get("body"), dict) else raw_payload
    address = body.get("address", "---")
    area_info = body.get("area", {})
    actual_land_area = area_info.get("actualLandArea", 0)
    building_type = body.get("type")  # e.g., "FIRST_LINE"
    latitude = body.get("latitude")
    longitude = body.get("longitude")

    # 1. Search Agent - Simulate the market research
    llm_search = ChatOpenAI(model="gpt-4o", api_key=API_KEY, temperature=0.3)
    
    search_system_prompt = """Siz internet qidiruv agentisiz. Vazifa — O‘zbekiston bozorida berilgan mulkka o‘xshash e’lonlarni topish.
Foydalaniladigan platformalar: olx.uz, domtut.uz, realt24.uz, uybor.uz, etc.

FAQAT JSON FORMATIDA CHIQARING.
{
 "status": "ok",
 "listings": [
   { "title": "...", "price_usd": ..., "area_m2": ..., "link": "..." }
 ]
}"""
    
    search_user_message = f"""Adress: {address}
Actual Land Area: {actual_land_area}
Type: {building_type}
Coords: {latitude}, {longitude}

Toshkent bo'yicha kamida 5 ta o'xshash elonlarni toping."""

    try:
        search_result = llm_search.invoke([
            SystemMessage(content=search_system_prompt),
            HumanMessage(content=search_user_message)
        ])
        # Try to parse JSON from search result
        search_text = search_result.content.strip()
        if "```json" in search_text:
            search_text = search_text.split("```json")[1].split("```")[0].strip()
        market_data = json.loads(search_text)
    except Exception as e:
        print(f"Search agent parsing error: {e}")
        market_data = {"status": "no_listing_found", "listings": []}

    # 2. Get Exchange Rate
    usd_rate = await get_usd_rate()

    # 3. Valuation Agent
    llm_val = ChatOpenAI(model="gpt-4o", api_key=API_KEY, temperature=0.3)
    
    valuation_system_prompt = f"""Siz O‘zbekiston bozorida ko‘chmas mulk narxini aniqlaydigan kredit baholash agentisiz.
Vazifa: kiruvchi ma’lumotlar va web qidiruvdan kelgan e’lonlar asosida obyektning bozor narxini aniqlash.

LTV (Kreditning qiymatga nisbati) ko'rsatkichi 64% gacha ijobiy.

USD/UZS Kursi: {usd_rate}

CHIQISH FORMATI (FAQAT JSON):
{{
 "estimated_min_price": <raqam_uzs>,
 "estimated_max_price": <raqam_uzs>,
 "reason": {{
    "uz": "<HTML>",
    "uz_cyrl": "<HTML>",
    "ru": "<HTML>",
    "en": "<HTML>"
 }}
}}

Hech qachon JSON tashqarisida matn qaytarmang."""

    valuation_user_message = f"""
"user_natija": {{
    "address": "{address}",
    "actualLandArea": {actual_land_area},
    "type": "{building_type}"
}},
"web_natija": {json.dumps(market_data, ensure_ascii=False)}
"""

    try:
        val_result = llm_val.invoke([
            SystemMessage(content=valuation_system_prompt),
            HumanMessage(content=valuation_user_message)
        ])
        
        val_text = val_result.content.strip()
        if "```json" in val_text:
            val_text = val_text.split("```json")[1].split("```")[0].strip()
            
        final_json = json.loads(val_text)
        return JSONResponse(content=final_json)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation failed: {str(e)}")
