import os
import json
import httpx
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

router = APIRouter()

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

# --- Models ---
class XMedRequest(BaseModel):
    session_id: str
    message: str

# --- Tools ---
@tool
async def search_doctor(page: str = "1", pageSize: str = "3", name: str = "", speciality: List[str] = None):
    """
    Search for suitable doctors based on name or speciality.
    Always call this tool before recommending a specific doctor.
    Args:
        page: Page number (default "1")
        pageSize: Number of results (default "3")
        name: Full or partial name of the doctor
        speciality: List of specialities (e.g. ["dentist", "surgeon"])
    """
    url = "https://api.plusmed.uz/be/common/searchDoctor"
    headers = {
        "language": "uz",
        "Content-Type": "application/json"
    }
    
    payload = {
        "page": page,
        "pageSize": pageSize,
        "name": name,
        "speciality": speciality or []
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data
    except Exception as e:
        return {"error": str(e), "results": []}

# --- Agent System Prompt ---
SYSTEM_PROMPT = """Sen malakali doctor yordamchisisan! 
Sening vazifang user yozgan shikoyatlari bo'yicha qaysi doktor unga mos kelishini aniqlash va uni to'g'ri doktorga yo'naltirish.

Eng muhim qoidalar:
Doktor id hech qachon to'qib chiqarilmasin.
Id chiqarishda chat tarixidan foydalanmang.
Id Chiqarish har doim "search_doctor" toolga murojat qilgandan keyin bolishi kerak.
Maslahat berish jarayonida <doctor malumotlari> har doim bolishi kerak.
Foydalanuvchi yozgan til va alifboda javob berish kerak.

Ish tartibi:
- Kop tillilik: Foydalanuvchi senga qaysi tilda(masalan o'zbekcha, ruscha) va qanday alifboda (masalan kirill, lotin) yozsa barcha javoblar faqat shunday tilda va shu alifboda bo'lsin.
- Foydalanuvchi senga kasalligi yoki muammolari haqida yozadi sen bu muammoga mos doctor tavsiya qilishing kerak.
- Foydalanuvchi og'rig'i haqida aytadi sen unga quydagi doktorlar orasidan keraklisini tanlaysan:
akusher-ginekolog, allergist, angiologist, andrologist, anesteziolog-reanimatolog, aritmolog, aphasiologist, bariatricheskiy-xirurg, valeolog, vertebrologist, vet, virologist, obstetrician, vrach-dietolog, laboratory-doctor, vrach-lfk, narodnaya-medicina, general-doctor, vrach-transfuziolog, vrach-ehndoskopist, gastroenterologist, gelmintolog, hematologist, geneticist, hepatologist, gynecologist, ginekolog-ehndokrinolog, girudoterapevt, dermatovenereologist, dermato-onkolog, childrens_gynecologist, childrens-infectious-disease, childrens-neurologist, pediatric-neurosurgeon, childrens-oncologist, childrens-psychologist, childrens-resuscitator, pediatric-urologist, childrens-endocrinologist, defectologist, nutritionist, acupuncturist, immunologist, intervencionnyj-kardiolog, infectionist, cardiologist, cardioresuscitator, cardio_surgeon, kinezioterapevt, kovidolog, coloproctologist, kombustiolog, cosmetologist, massage-therapist, speech-therapist, ent, mammologist, manualnyj-terapevt, masseur, medicinskij-kosmetolog, medicinskij-psiholog, nurse, mikolog, narcologist, neurologist, nevrolog-refleksoterapevt, nejro-onkolog, neurosurgeon, neyroendokrinolog, neonatologist, nephrologist, oligofrenopedagog, onkogematolog, oncogynecologist, onkokoloproktolog, oncologist, oncologist-mammologist, onkolog-himioterapevt, onkourolog, ortodont, ortoped-vertebrolog, childrens-orthopedist, orthopedist-traumatologist, osteopat, otonevrolog, ophthalmologist, oftalmohirurg, parasitologist, pediatrician, plastic_surgeon, podolog, podrostkovyj-psiholog, proctologist, profpatolog, psixiatr, psychologist, psychotherapist, pulmonologist, pulmonolog-astmolog, radiologist, rehabilitologist, resuscitator, rheumatologist, rentgenologist, reproductologist, sexologist, cardiovascular-surgeon, screening, somnolog, dentist-surgeon, dentist, audiologist, therapist, toxicologist, thoracic-oncologist, torakalhiy-xirurg, traumatologist, trichologist, urologist, urolog-androlog, pharmacologist, physiotherapist, phlebologist, foniatr, phthisiatrician, ftiziatr-pulmonolog, functional-diagnostic, surgeon, childrens-surgeon, circumcisiologist, maxillofacial-surgeon, ehmbriolog, ehndovaskulyarnyj-hirurg, endocrinologist, epidemiologist, ehpileptolog.

- Search Doctor toolga jonatiladigan speciality qiymati yuqoridagi ro'yxatdan olinishi shart.
- "Search Doctor" toolga kirmaguncha javob chiqarma. Barcha javob "search_doctor" tooldan kelgan natija asosida bo'lishi kerak.
- Kassalik haqida qisqacha nimadan kelib chiqishi mumkin va tashxis juda ham cho'zilib ketmasin umumiy malumotlar ber qanday choralar ko'rish kerakligi haqida qisqacha tushintir va davomidan * Doktor : tanlangan doktorning ism familiyasi, reytingi, va ish tajribasi chiqsin. 
- Tavsiya qismi 150 ta belgidan oshmasin.

CHIQUVCHI FORMAT FAQAT JSON:
{
"answer": "<sening javobing>",
"doctor_id": <doctorning idsi(agar bor bo'lsa aks holda null)>,
"answer_2": "<Hisobingizni qanday to'ldirishni bilasizmi? (agar doctor_id bo'lsa)>",
"answer_3": "#fill",
"answer_4": "<Hisobingizni to'ldirib ushbu shifokor bilan maslahatlashing. (agar doctor_id bo'lsa)>"
}

Ishlash qoidalari:
- savol:To'lov qilish va hisobni to'ldirish -> javob: "answer": "#fill", qolganlar null.
- Chat davomida mavzudan tashqari savullar bo'lsa "Men faqat mavzu doirasida javob bera olaman" deysan.
"""

# --- Agent Initialization ---
llm = ChatOpenAI(model="gpt-4o", api_key=API_KEY, temperature=0)
checkpointer = MemorySaver()

# Simplified agent without modifiers for better compatibility
agent_executor = create_react_agent(
    model=llm, 
    tools=[search_doctor], 
    checkpointer=checkpointer
)

# --- Helpers ---
def extract_json(text: str) -> Dict[str, Any]:
    """Helper to extract JSON from AI response, handles Markdown blocks."""
    text = text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    try:
        return json.loads(text)
    except:
        return {"answer": text, "doctor_id": None, "answer_2": None, "answer_3": None, "answer_4": None}

@router.post("/webhook/xmed")
async def handle_xmed(payload: XMedRequest):
    """XMed Integrated Portal: Medical Assistant Agent."""
    config = {"configurable": {"thread_id": payload.session_id}}
    
    try:
        # Prepend SYSTEM_PROMPT to every request to ensure instructions are respected
        input_data = {"messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=payload.message)
        ]}
        
        result = await agent_executor.ainvoke(input_data, config=config)
        
        last_message = result["messages"][-1].content
        parsed_output = extract_json(last_message)
        
        response_json = {
            "answer": parsed_output.get("answer"),
            "doctor_id": parsed_output.get("doctor_id"),
            "answer_2": parsed_output.get("answer_2"),
            "answer_3": parsed_output.get("answer_3"),
            "answer_4": parsed_output.get("answer_4")
        }
        
        return JSONResponse(content=response_json)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Medical Agent failed: {str(e)}")
