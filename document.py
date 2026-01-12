import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from pydantic import RootModel
import json

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENWEATHER_API_KEY:
    raise RuntimeError("OPENWEATHER_API_KEY is not set")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

llm = ChatOpenAI(
    model="gpt-5.1",
    api_key=API_KEY,
    temperature=0.3,
)

app = FastAPI()


class WebhookRequest(RootModel):
    root: dict | list  


class WebhookResponse(RootModel):
    root: str  


@app.post("/webhook", response_model=WebhookResponse)
async def webhook(payload: WebhookRequest):
    body = payload.root

    try:
        input_data = json.dumps(body, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    system_prompt = f"""Siz professional AI yordamchisiz.   

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


1-BO‘LIM — Loyiha haqida ma’lumot


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


2-BO‘LIM — Ta'sischilar haqida ma’lumot


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


3-BANK REKVIZITLARI


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


4-ARIZA MA'LUMOTLARI


<p>
    <strong><u>Loyiha haqida qisqacha ma'lumot</u></strong>
    <strong><u>Loyiha tavsifi</u></strong>
    <strong><u>
    {body.get("company_info", {}).get("data", {}).get("name", "---")}
    {body.get("bankInfo", {}).get("regDate", "---")}-yilda faoliyatini boshlagan.
    </u></strong>
</p>

<p>
Kompaniyaning asosiy faoliyati{body.get("company_info", {}).get("data", {}).get("okedDetail", {}).get("name", "---")}
hisoblanadi.
<strong><u>Ushbu loyihani amalga oshirish uchun
{body.get("company_info", {}).get("data", {}).get("name", "---")}
</u></strong> bankka kompaniyaning
{(
    body.get("applicationInfo", {})
        .get("applicationData", {})
        .get("purposeUz")
    or
    body.get("applicationInfo", {})
        .get("applicationData", {})
        .get("purposeRu")
    or
    body.get("applicationInfo", {})
        .get("applicationData", {})
        .get("purposeEn")
)
}maqsadida asosiy vositalar va aylanma mablag'larni sotib olish uchun
umumiy kredit shartnomasini tuzishni ko'rib chiqish taklifi bilan murojaat qildi,
maksimal kredit limiti
{body.get("applicationInfo", {}).get("applicationData", {}).get("requestedAmount")}
{body.get("applicationInfo", {}).get("applicationData", {}).get("currency")},
{body.get("applicationInfo", {}).get("applicationData", {}).get("loanTermMonths")}
oy muddatga mo'ljallangan. Kreditlar aylanma mablag'lar uchun {body.get("applicationInfo", {}).get("applicationData", {}).get("loanTermMonths")} oygacha (kelishuvga muvofiq) va asosiy vositalarni sotib olish uchun {body.get("applicationInfo", {}).get("applicationData", {}).get("loanTermMonths")} oygacha muddatga rejalashtirilgan. Kreditlar bo'yicha foiz stavkalari AQSh dollarida yillik 15%, yevroda yillik 15% va milliy valyutada yillik {body.get("applicationInfo", {}).get("applicationData", {}).get("downPaymentPercent")} % ni tashkil qiladi.

<strong><u>Majburiyatlarni to'lash manbai kompaniyaning davom etayotgan faoliyatidan kelib chiqadi.</u></strong></p>

Yuqorida e'tibor berish kerak bo'lgan muhim joy bor! Ya'ni, kompaniyaning kredit olish maqsadi 4 xil tilda keladi, siz uni tarjima qilinadigan tilga qarab tanlashingiz kerak. Misol
"language":"uz" bo'lsa -> applicationInfo.applicationData.purposeUz qiymati olinadi.
"language":"cyrl" bo'lsa -> applicationInfo.applicationData.purposeCyrl qiymati olinadi.
"language":"ru" bo'lsa -> applicationInfo.applicationData.purposeRu qiymati olinadi.
"language":"en" bo'lsa -> applicationInfo.applicationData.purposeEn qiymati olinadi.




5-BANK TOMONIDAN TO'LDIRILISHI KERAK BO'LGAN MA'LUMOTLAR


<p><strong>Bank tomonidan to'ldiriladi</strong></p>

<p>
    <strong>Korxona nomidagi asosiy obyekt (ofis, bino, ombor, turar joy)</strong> quyidagi manzilda joylashgan:
    {body.get("taxObjects", {}).get("dataObject", [{}])[0].get("address", "---")}, umumiy maydoni {body.get("taxObjects", {}).get("dataObject", [{}])[0].get("total_area", "---")} kv.m., bino va inshootlar maydoni {body.get("taxObjects", {}).get("dataObject", [{}])[0].get("land_area", "---")} kv.m., kadastr raqami {body.get("taxObjects", {}).get("dataObject", [{}])[0].get("obj_code", "---")}.
</p>



6-BO‘LIM — Garov haqida ma’lumot


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


<p><em><u>Garovga qo'yilgan mashina ma'lumotlari:</u></em></p>

<table border="1" cellspacing="0" cellpadding="4" width="100%"
       style="font-family:'Times New Roman'; font-size:11pt;">
<tr>
    <th>Modeli</th>
    <th>Rangi</th>
    <th>Yil</th>
    <th>Kuzov raqami</th>
    <th>Motor</th>
    <th>Shassi</th>
    <th>Davlat raqami</th>
    <th>Ro'yxatdan o'tgan sana</th>
    <th>Diviziya</th>
    <th>Egalik qiluvchi</th>
    <th>Manzili</th>
    <th>Garovning taxminiy qiymati</th>
</tr>

{''.join(
    f"<tr>"
    f"<td>{i.get('yurCarData', {}).get('model', '---')}</td>"
    f"<td>{i.get('yurCarData', {}).get('color', '---')}</td>"
    f"<td>{i.get('carYear', i.get('yurCarData', {}).get('year', '---'))}</td>"
    f"<td>{i.get('cadastreOrCarKuzov', i.get('yurCarData', {}).get('kuzov', '---'))}</td>"
    f"<td>{i.get('yurCarData', {}).get('motor', '---')}</td>"
    f"<td>{i.get('yurCarData', {}).get('shassi', '---')}</td>"
    f"<td>{i.get('carLicensePlate', i.get('yurCarData', {}).get('gosNumber', '---'))}</td>"
    f"<td>{i.get('yurCarData', {}).get('regDate', '---')}</td>"
    f"<td>{i.get('yurCarData', {}).get('division', '---')}</td>"
    f"<td>{i.get('yurCarData', {}).get('owner', '---')}</td>"
    f"<td>{i.get('yurCarData', {}).get('adres', i.get('address', '---'))}</td>"
    f"<td>{i.get('estimatedValue', '---')}</td>"
    f"</tr>"
    for i in body.get("applicationInfo", {}).get("collateralData", [])
    if i.get("yurCarData") or i.get("collateralType") == "VEHICLE"
)}
</table>




7-BALANS HISOBOTI


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



8-BO‘LIM — Korxona haqidagi qisqacha ma'lumot


<p><strong>Korxona haqida qisqacha ma’lumot:</strong><br/>
    {body.get("company_info", {}).get("data", {}).get("name", "---")} korxonasi {body.get("foundation_year", "---")} yildan beri faoliyat yuritib, asosan {body.get("company_info", {}).get("data", {}).get("okedDetail", {}).get("name", "---")} sohasida xizmat ko‘rsatib keladi. Korxona yuridik manzili: {body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("region", {}).get("name", "---")}, {body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("district", {}).get("name", "---")}, {body.get("company_info", {}).get("data", {}).get("companyBillingAddress", {}).get("streetName", "---")}. Tashkilotda {body.get("employeeCount", "---")} nafar xodim ishlaydi.
</p>

<p><em><u>Korxona nomidagi obyektlar:</u></em></p>

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
</tr>

{''.join(
    f"<tr>"
    f"<td>{i.get('tin', '---')}</td>"
    f"<td>{i.get('name', '---')}</td>"
    f"<td>{i.get('type', '---')}</td>"
    f"<td>{i.get('obj_code', '---')}</td>"
    f"<td>{i.get('obj_name', '---')}</td>"
    f"<td>{i.get('address', '---')}</td>"
    f"<td>{i.get('percentage', '---')}</td>"
    f"<td>{i.get('inv_cost', '---')}</td>"
    f"<td>{i.get('total_area', '---')}</td>"
    f"<td>{i.get('land_area', '---')}</td>"
    f"<td>{i.get('land_extra_area', '---')}</td>"
    f"</tr>"
    for i in body.get("taxObjects", {}).get("dataObject", [])
)}
</table>

<p><em><u>Korxona nomidagi mashinalar:</u></em></p>

<table border="1" cellspacing="0" cellpadding="4" width="100%"
       style="font-family:'Times New Roman'; font-size:11pt;">
<tr>
    <th>Modeli</th>
    <th>Rangi</th>
    <th>Yil</th>
    <th>Kuzov raqami</th>
    <th>Motor</th>
    <th>Shassi</th>
    <th>Davlat raqami</th>
    <th>Ro'yxatdan o'tgan sana</th>
    <th>Diviziya</th>
    <th>Egalik qiluvchi</th>
    <th>Manzili</th>
</tr>

{''.join(
    f"<tr>"
    f"<td>{i.get('model', '---')}</td>"
    f"<td>{i.get('color', '---')}</td>"
    f"<td>{i.get('year', '---')}</td>"
    f"<td>{i.get('kuzov', '---')}</td>"
    f"<td>{i.get('motor', '---')}</td>"
    f"<td>{i.get('shassi', '---')}</td>"
    f"<td>{i.get('gosNumber', '---')}</td>"
    f"<td>{i.get('regDate', '---')}</td>"
    f"<td>{i.get('division', '---')}</td>"
    f"<td>{i.get('owner', '---')}</td>"
    f"<td>{i.get('adres', '---')}</td>"
    f"</tr>"
    for i in body.get("taxObjects", {}).get("carDataObject", [])
)}
</table>



9-BO‘LIM — Yakuniy kredit bo‘yicha ekspert xulosasi


<h3>Yakuniy kredit bo‘yicha ekspert xulosasi</h3>

Xulosa quyidagilar asosida avtomatik shakllantiriladi:

✓ Kompaniya faoliyat holati  
✓ Har doim forma bo‘yicha 
✓ Pul oqimi  
✓ Zalog likvidligi  
✓ Risklar  Kredit berish tavsiya qilinadi
✓ Kuchli tomonlar  
yuqoridagi natijalar hammasi qisqa londa bo'lsin. Hammasi bitta paragraphda yozilsin.

Kredit berish xulosasini tuzish bo'yicha logika:
- Moliyaviy yuk (Aylanma darajasi). Agar so'ralgan kredit summasi kompaniyaning yillik aylanmasidan oshiq bo'lsa, bunday holatni past kredit havfi va kredit bo'yicha qarzni to'lamaslik ehtimoli sifatida baholashingiz kerak.
- Garov (LTV - Kreditning qiymatga nisbati):
Agar taqdim etilgan garov kredit miqdoridan sezilarli darajada ortiq bo'lsa, LTV (Kreditning qiymatga nisbati) 64% gacha bo'lgan nisbat ( 
<b>{(
    body.get("applicationInfo", {})
        .get("collateralData", [{}])[0]
        .get("estimatedValue", 0) * 0.64
    >
    body.get("applicationInfo", {})
        .get("applicationData", {})
        .get("requestedAmount", 0)
) }</b>


        ijobiy hisoblanadi.

XULOSA QUYIDAGILARDAN BIRI BO‘LISHI SHART, VA ULAR HAM BELGILANGAN TILGA TARJIMA QILINISHI SHART:

1) Agar kredit berish tavsiya etilsa: <strong> Kredit berish tavsiya qilinadi </strong> <- albatta {body.get("language", {})}ga tarjima qilinish kerak
2) Agar kredit berish tavsiya etilmasa: <strong> Kommitet tomonidan ko'rib chiqiladi </strong> <- albatta {body.get("language", {})}ga tarjima qilinish kerak

Yuqoridagi ikkita holat, hulosa ham albatta belgilangan tilga tarjima qilish kerak, va o'sha tilda chiqarish kerak, boshqa tildagi qo'shimchalar bo'lmasin! Hech qachon belgilangan tildan boshqasiga tarjima qilmang!

Va albatta izohlar bilan:
– Nima sababdan berilishi kerak / berilmasligi kerak aynan jadvaldagi qaysi ma'lumot asosida olayapti.
– Qaysi ko‘rsatkichga asoslanildi aynan jadvaldagi qaysi ma'lumot asosida olayapti.
– Qaysi risklar mavjud aynan jadvaldagi qaysi ma'lumot asosida olayapti.
– Qaysi kuchli jihatlar kreditni qo‘llab-quvvatlaydi aynan jadvaldagi qaysi ma'lumot asosida olayapti.
- Hulosa rasmiy tilda yozilsin. jadval malumotlari korsatishda qavslar ichida emas, tabiiy shaklda yozilsin. Hulosa xar doim 9-bo'lim oxirida bulishi shart.
====================================================================================

Qat'iy qoidalar:
• Har doim belgilangan tilgan tarjima qilishinshi shart. 
• HTML faqat Word formatiga mos bo‘lsin
• Har bir bo'lim va qismlar shablonda ko'rsatilgandek tartibda, joy-joyida chiqishi shart!
• Barcha bo‘sh ma’lumotlar — `---`  
• Raqamlar 1 234 567.89 tarzida formatlansin  
• Ovoz ohangi — professional bank ekspertizasi
• Javob juda ham sifatli va juda ham tez bo'lishi lozim. Foydalanuvchi kutib qolmasligi uchun!
• Chiquvchi natijalarga "\n" belgilarini qo'yma orniga </br> ishlat. oxirgi natija wordga yozish uchun tayyor html shaklda bolishi kerak. 
• Textlar toza natija bo'lishi kerkak.
• Chiquvchi text malumotlar ham tartibli kerakli joylar alohida korsatilgan holatda bolishi kerak.
• "---" bu ma'lumot yo'q degani. 
• "language" fieldida so'ralgan tilda javob generatsiya qilish lozim!
"""

    agent = create_agent(model=llm, tools=[], system_prompt=system_prompt)

    result = agent.invoke({"messages": [{"role": "user", "content": input_data}]})

    html = result["messages"][-1].content

    return HTMLResponse(content=html, status_code=200)

