import os
import re
import requests
from http.client import HTTPException
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
# from telegram.ext import Application, MessageHandler, filters


# ENV
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
api_key= os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

if not OPENWEATHER_API_KEY:
    raise RuntimeError("OPENWEATHER_API_KEY is not set")


app = FastAPI(title="Weather Agent Webhook")




# LLM
llm = ChatOpenAI(
    model="gpt-5.1",
    api_key=api_key,
    temperature=0.3,
)


# AGENT
agent = create_agent(
    model=llm,
    tools=[], 
    system_prompt = (
    f"""Siz professional AI yordamchisiz. 

Sizga keladigan ma’lumot — kompaniya haqida JSON.
{input_data}

Sizning vazifangiz: shu JSON asosida chiroyli, Word uchun mos HTML-hujjat yaratish,
jadval shaklida barcha ma’lumotlarni to‘g‘ri joylashtirish, bo‘sh ma’lumotlarga `---`
belgisini qo‘yish va hujjat oxirida yakuniy kredit bo‘yicha ekspert xulosasini berish.
Kelgan JSONda "language" fieldida qaysi tilda xulosa yaratish aytilgan, o'sha tilda chiqarish kerak bo'ladi. Asosiy 4 ta til:
"uz" - O'zbek tili
"cyrl" - O'zbek tili kiril alifbosi
"ru" - Rus tili
"en" - Ingliz tili


Qat'iy qoida va muhim qoida:
• HECH QACHON, HECH BIR SO'Z HAM SO'RALGAN TILDAN BOSHQA TILDA CHIQMASIN!
• HTML HECH QACHON BERILGAN FORMATDAN BOSHQA BULMASLIGI SHART
• HTMLdan TASHQARI MATN YOKI IZOH YOZILMASIN
• TABLElar FORMATI, SONI, STRUCTURASI BERILGAN FORMATDA BULISI SHART


====================================================================================
📘 1-BO‘LIM — Loyiha haqida ma’lumot
====================================================================================

<h2>Loyiha bo‘yicha ma’lumot: {body.get("company_info", {}).get("data", {}).get("name", "---")}</h2>

<h3>Kompaniya haqida</h3>
<table border="1" cellspacing="0" cellpadding="4" width="100%"
       style="font-family:'Times New Roman'; font-size:11pt;">
<tr><td>Tashkilotning to‘liq nomi</td><td>{body.get("company_info", {}).get("data", {}).get("name", "---")}</td></tr>
<tr><td>INN</td><td>{body.get("company_info", {}).get("data", {}).get("tin", "---")}</td></tr>
<tr><td>Sohasi (OKED)</td><td>{body.get("company_info", {}).get("data", {}).get("okedDetail", {}).get("name", "---")}</td></tr>
<tr><td>Kompaniya kategoriyasi</td><td>{body.get("company_info", {}).get("data", {}).get("businessTypeDetail", {}).get("name", "---")}</td></tr>
<tr><td>O'rta ishchilar soni</td><td>{body.get("employeeCount", "---")}</td></tr>
<tr><td>Yuridik manzil</td>
<td>{body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("region", {}).get("name", "---")},
{body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("district", {}).get("name", "---")},
{body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("streetName", "---")}</td></tr>
<tr><td>Ustav fondi</td><td>{body.get("company_info", {}).get("data", {}).get("businessFund", "---")}</td></tr>
</table>

====================================================================================
📘 2-BO‘LIM — Ta'sischilar haqida ma’lumot
====================================================================================

<h2>Ta'sischilar bo‘yicha ma’lumot</h2>

<table border="1" cellspacing="0" cellpadding="4" width="100%"
       style="font-family:'Times New Roman'; font-size:11pt;">
<tr>
    <th>F.I.O. / Nomi</th>
    <th>Kim hisoblanadi</th>
    <th>Ulushi (%)</th>
    <th>Boshqa subyektlardagi ishtiroki</th>
</tr>

{''.join(
    (
        f"<tr>"
        f"<td>{founder_name}</td>"
        f"<td>{founder_type}</td>"
        f"<td>{f.get('sharePercent', '---')}</td>"
        f"<td>---</td>"
        f"</tr>"
    )
    for f in body.get("company_info", {}).get("data", {}).get("founders", [])
    for founder_name, founder_type in [(
        (
            ' '.join(filter(None, [
                f.get('founderIndividual', {}).get('lastName'),
                f.get('founderIndividual', {}).get('firstName'),
                f.get('founderIndividual', {}).get('middleName')
            ])) if f.get('founderIndividual')
            else f.get('founderLegal', {}).get('name', '---')
        ),
        (
            "Jismoniy shaxs" if f.get('founderIndividual')
            else "Yuridik shaxs" if f.get('founderLegal')
            else "---"
        )
    )]
)}


<tr>
    <td><b>Direktor</b></td>
    <td colspan="3">{
        ' '.join(filter(None, [
            body.get("company_info", {}).get("data", {}).get("director", {}).get("lastName"),
            body.get("company_info", {}).get("data", {}).get("director", {}).get("firstName"),
            body.get("company_info", {}).get("data", {}).get("director", {}).get("middleName")
        ])) or '---'
    }</td>
</tr>
</table>


====================================================================================
📘 3-BANK REKVIZITLARI
====================================================================================

<p><em><u>Bank rekvizitlari:</u></em></p>
<p><strong>Asosiy hisob:</strong></p>

<table border="1" cellspacing="0" cellpadding="4" width="100%"
       style="font-family:'Times New Roman'; font-size:11pt;">
<tr>
    <td><b>Bank nomi</b></td>
    <td>{body.get("bankInfo", {}).get("ns2Name", "---")}</td>
</tr>
<tr>
    <td><b>Hisob raqami</b></td>
    <td>{
        ''.join(body.get("bankInfo", {}).get("account", "").split())
        if body.get("bankInfo", {}).get("account")
        else "---"
    }</td>
</tr>
<tr>
    <td><b>MFO</b></td>
    <td>{body.get("bankInfo", {}).get("ns2Code", "---")}</td>
</tr>
</table>

====================================================================================
📘 4-ARIZA MA'LUMOTLARI
====================================================================================

<p><strong><u>Loyiha haqida qisqacha ma'lumot</u></strong></p>

<p>
{body.get("company_info", {}).get("data", {}).get("name", "---")}
{body.get("bankInfo", {}).get("regDate", "---")}-yilda faoliyatini boshlagan.
</p>

<p>
Kompaniyaning asosiy faoliyati
{body.get("company_info", {}).get("data", {}).get("okedDetail", {}).get("name", "---")}
hisoblanadi.
</p>

<p>
Ushbu loyihani amalga oshirish uchun
{body.get("company_info", {}).get("data", {}).get("name", "---")}
bankka kompaniyaning
{body.get("applicationInfo", {}).get("applicationData", {}).get(
    "purpose" + body.get("language", "uz").capitalize(),
    "---"
)}
maqsadida asosiy vositalar va aylanma mablag'larni sotib olish uchun
umumiy kredit shartnomasini tuzishni ko'rib chiqish taklifi bilan murojaat qildi,
maksimal kredit limiti
{body.get("applicationInfo", {}).get("applicationData", {}).get("requestedAmount", "---")}
{body.get("applicationInfo", {}).get("applicationData", {}).get("currency", "---")},
{body.get("applicationInfo", {}).get("applicationData", {}).get("loanTermMonths", "---")}
oy muddatga mo'ljallangan.
</p>


====================================================================================
📘 5-BANK TOMONIDAN TO'LDIRILISHI KERAK BO'LGAN MA'LUMOTLAR
====================================================================================

<p><strong>Bank tomonidan to'ldiriladi</strong></p>

<p>
Korxona nomidagi asosiy obyekt (ofis, bino, ombor, turar joy) quyidagi manzilda joylashgan:
{body.get("taxObjects", {}).get("dataObject", [{}])[0].get("address", "---")},
umumiy maydoni
{body.get("taxObjects", {}).get("dataObject", [{}])[0].get("total_area", "---")}
kv.m.,
bino va inshootlar maydoni
{body.get("taxObjects", {}).get("dataObject", [{}])[0].get("land_area", "---")}
kv.m.,
kadastr raqami
{body.get("taxObjects", {}).get("dataObject", [{}])[0].get("obj_code", "---")}.
</p>


====================================================================================
📘 6-BO‘LIM — Garov haqida ma’lumot
====================================================================================

<h3>Garov haqida ma’lumot</h3>

<p><em><u>Garovga qo'yilgan bino ma'lumotlari:</u></em></p>

<table border="1" cellspacing="0" cellpadding="4" width="100%"
       style="font-family:'Times New Roman'; font-size:11pt;">
<tr>
    <th>TIN</th>
    <th>Kompaniya nomi</th>
    <th>Turi</th>
    <th>Kadastr raqami</th>
    <th>Bino nomi</th>
    <th>Manzili</th>
    <th>Egalik qiluvchi ulushi (%)</th>
    <th>Inventar narx</th>
    <th>Umumiy maydon</th>
    <th>Bino maydoni</th>
    <th>Qo'shimcha maydon</th>
    <th>Garovning taxminiy qiymati</th>
</tr>

{''.join(
    f"<tr>"
    f"<td>{i.get('yurTaxObjectData', {}).get('tin', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('name', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('type', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('obj_code', i.get('cadastreOrCarKuzov', '---'))}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('obj_name', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('address', i.get('address', '---'))}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('percentage', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('inv_cost', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('total_area', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('land_area', '---')}</td>"
    f"<td>{i.get('yurTaxObjectData', {}).get('land_extra_area', '---')}</td>"
    f"<td>{i.get('estimatedValue', '---')}</td>"
    f"</tr>"
    for i in body.get("applicationInfo", {}).get("collateralData", [])
    if i.get("yurTaxObjectData") or i.get("collateralType") == "REAL_ESTATE"
)}
</table>


====================================================================================
📘 7-BALANS HISOBOTI
====================================================================================

<p><em><u>Balans bo'yicha hisobot:</u></em></p>

<table border="1" cellspacing="0" cellpadding="5">
<tr>
    <th>Ko'rsatkich nomi</th>
    <th>Qator</th>
    <th colspan="2">
        {body.get("company_info", {}).get("data", {}).get("name", "---")}
    </th>
</tr>

<tr><th></th><th></th><th></th><th></th></tr>

<tr>
    <td>Asosiy vositalarning qoldiq qiymati (010-011)</td>
    <td>010</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "010"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "010"), "---")}</td>
</tr>

<tr>
    <td>Jami inventarizatsiya (150+160+170+180-qatorlar), shu jumladan:</td>
    <td>140</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "140"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "140"), "---")}</td>
</tr>

<tr>
    <td>Jami debitorlar (220+240+250+260+270+280+290+300+310 qatorlar)</td>
    <td>210</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "210"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "210"), "---")}</td>
</tr>

<tr>
    <td>Balans aktivlarining umumiy summasi (130-qator + 390-qator)</td>
    <td>400</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "400"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "400"), "---")}</td>
</tr>

<tr>
    <td>Shu jumladan: joriy kreditorlik qarzlari (610+630+650+670+680+690+700+710+720+760-qatorlar)</td>
    <td>601</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "601"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "601"), "---")}</td>
</tr>

<tr>
    <td>Uzoq muddatli bank kreditlari (7810)</td>
    <td>570</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "570"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "570"), "---")}</td>
</tr>

<tr>
    <td>Qisqa muddatli bank kreditlari (6810)</td>
    <td>730</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "730"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "730"), "---")}</td>
</tr>

<tr>
    <td>Jami majburiyatlar (480+770-qatorlar)</td>
    <td>780</td>
    <td>{next((r.get("sum_begin_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "780"), "---")}</td>
    <td>{next((r.get("sum_end_period") for r in body.get("forma_1", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "780"), "---")}</td>
</tr>

<tr>
    <td>Moliyaviy ko'rsatkichlar ma'lumotlari</td>
    <td></td><td></td><td></td>
</tr>

<tr>
    <td>Mahsulotlar (tovarlar, ishlar va xizmatlar) sotishdan olingan sof daromad</td>
    <td>010</td>
    <td>{next((r.get("sum_period_doxod") for r in body.get("forma_2", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "010"), "---")}</td>
    <td>{next((r.get("sum_period_rasxod") for r in body.get("forma_2", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "010"), "---")}</td>
</tr>

<tr>
    <td>Hisobot davri uchun sof foyda (zarar) (240-250-260-qatorlar)</td>
    <td>270</td>
    <td>{next((r.get("sum_period_doxod") for r in body.get("forma_2", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "270"), "---")}</td>
    <td>{next((r.get("sum_period_rasxod") for r in body.get("forma_2", {}).get("data", [{}])[0].get("rows", []) if r.get("row_no") == "270"), "---")}</td>
</tr>
</table>


====================================================================================
📘 8-BO‘LIM — Korxona haqidagi qisqacha ma'lumot
====================================================================================

<p><strong>Korxona haqida qisqacha ma’lumot:</strong><br/>
{body.get("company_info", {}).get("data", {}).get("name", "---")} korxonasi
{body.get("foundation_year", "---")} yildan beri faoliyat yuritib,
asosan {body.get("company_info", {}).get("data", {}).get("okedDetail", {}).get("name", "---")}
sohasida xizmat ko‘rsatib keladi.
Korxona yuridik manzili:
{body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("region", {}).get("name", "---")},
{body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("district", {}).get("name", "---")},
{body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("streetName", "---")}.
Tashkilotda {body.get("employeeCount", "---")} nafar xodim ishlaydi.
</p>

====================================================================================
📘 9-BO‘LIM — Yakuniy kredit bo‘yicha ekspert xulosasi
====================================================================================

<h3>Yakuniy kredit bo‘yicha ekspert xulosasi</h3>

<p>
Xulosa quyidagilar asosida avtomatik shakllantiriladi:
<ul>
<li>Kompaniya faoliyat holati</li>
<li>Pul oqimi</li>
<li>Zalog likvidligi</li>
<li>Risklar</li>
<li>Kuchli tomonlar</li>
<li>Kredit bo‘yicha tavsiya</li>
</ul>
</p>

<p>
{"Kredit berish tavsiya qilinadi" if body.get("allow_credit", False) else "Kommitet tomonidan ko'rib chiqiladi"}
</p>

<p>
Izoh: Xulosa barcha ma’lumotlar asosida, belgilangan tilda ({body.get("language", "uz")}) chiqariladi.
</p>
"""
)
)

# WEBHOOK
@app.post("/webhook", response_model=WebhookResponse)
def webhook(payload: WebhookRequest):
    try:
        result = agent.invoke({
            "messages": [
                {"role": "user", "content": payload.message}
            ]
        })

        return {
            "reply": result["messages"][-1].content
        }

    except Exception as e:
        print("ERROR:", e)
        raise HTTPException(status_code=500, detail="Agent error")
    
# REQUEST SCHEMA
class WebhookRequest(BaseModel):
    message: str

class WebhookResponse(BaseModel):
    reply: str



# # TOOL: OpenWeather
# def get_weather(city: str) -> str:
#     """Get current weather for a city using OpenWeather API"""

#     url = "https://api.openweathermap.org/data/2.5/weather"
#     params = {
#         "q": city,
#         "appid": OPENWEATHER_API_KEY,
#         "units": "metric",
#         "lang": "en",
#     }

#     try:
#         r = requests.get(url, params=params, timeout=10)
#         r.raise_for_status()
#     except Exception:
#         return f"❌ I couldn't get weather for **{city}**"

#     data = r.json()

#     temp = data["main"]["temp"]
#     feels = data["main"]["feels_like"]
#     desc = data["weather"][0]["description"].capitalize()
#     wind = data["wind"]["speed"]
#     city_name = data["name"]

#     return (
#         f"🌤 **Weather in {city_name}**\n"
#         f"🌡 Temperature: {temp}°C (feels like {feels}°C)\n"
#         f"☁ Condition: {desc}\n"
#         f"💨 Wind: {wind} m/s"
#     )


# # TELEGRAM HANDLER

# async def handle(update, context):
#     try:
#         user_text = update.message.text

#         result = agent.invoke({
#             "messages": [
#                 {"role": "user", "content": user_text}
#             ]
#         })

#         await update.message.reply_text(
#             result["messages"][-1].content
#         )

#     except Exception as e:
#         print("ERROR:", e)
#         await update.message.reply_text("⚠️ Something went wrong. Try again.")


# APP

# app = Application.builder().token(TELEGRAM_TOKEN).build()
# app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# print("🤖 Weather bot is running...")
# app.run_polling()
