import os
import json
import httpx
from typing import Any, Dict
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

class WebhookRequest(RootModel):
    root: Dict[str, Any]

async def get_usd_rate() -> float:
    url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            for item in data:
                if item.get("Ccy") == "USD":
                    return float(item.get("Rate", 0))
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
    return 12850.0

@router.post("/webhook/avto")
async def handle_avto(payload: WebhookRequest):
    raw_payload = payload.root
    
    if isinstance(raw_payload, list):
        body = raw_payload[0] if raw_payload else {}
    else:
        body = raw_payload.get("body") if isinstance(raw_payload.get("body"), dict) else raw_payload
    
    model = body.get("MODEL", "---")
    color = body.get("COLOR", "---")
    year = body.get("YEAR", "---")
    motor = body.get("MOTOR", "---")
    shassi = body.get("SHASSI", "---")
    kuzov = body.get("KUZOV", "---")

    llm = ChatOpenAI(model="gpt-4o", api_key=API_KEY, temperature=0.3)

    # 1. Search Agent
    search_system_prompt = """Siz internet qidiruv agentisiz. Vazifa — kiritilgan avtomobil ma’lumotlari asosida O‘zbekiston internetidagi e’lon saytlaridan eng o‘xshash e’lonlarni topish. FAQAT JSON FORMATIDA CHIQARING."""
    search_user_message = f"Model: {model}, Year: {year}, Color: {color}, Motor: {motor}, Shassi: {shassi}, Kuzov: {kuzov}"

    try:
        search_result = llm.invoke([SystemMessage(content=search_system_prompt), HumanMessage(content=search_user_message)])
        stext = search_result.content.strip()
        if "```json" in stext: stext = stext.split("```json")[1].split("```")[0].strip()
        market_data = json.loads(stext)
    except: market_data = {"status": "no_listing_found", "listings": []}

    # 2. Rate
    usd_rate = await get_usd_rate()

    # 3. Valuation Agent
    val_system_prompt = f"""Siz O‘zbekiston bozorida avtomobil narxini aniqlaydigan ekspert agentsiz. 
    Vazifa: mashinaning bozor narxini aniqlash. Kurs: {usd_rate}. 
    Depresatsiya: har yil farqi uchun 2%.
    CHIQISH FAQAT JSON: 
    {{
      "estimated_min_price": <number_uzs>, 
      "estimated_max_price": <number_uzs>, 
      "reason_uz": "<HTML>", 
      "reason_uz_kiril": "<HTML>", 
      "reason_ru": "<HTML>", 
      "reason_en": "<HTML>"
    }}"""
    
    val_user_msg = f"Car Info: {json.dumps(body)}, Listings: {json.dumps(market_data)}"

    try:
        val_result = llm.invoke([SystemMessage(content=val_system_prompt), HumanMessage(content=val_user_msg)])
        vtext = val_result.content.strip()
        if "```json" in vtext: vtext = vtext.split("```json")[1].split("```")[0].strip()
        return JSONResponse(content=json.loads(vtext))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
