import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from telegram.ext import Application, MessageHandler, filters

# =======================
# ENV
# =======================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
api_key= os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

if not OPENWEATHER_API_KEY:
    raise RuntimeError("OPENWEATHER_API_KEY is not set")

# =======================
# LLM
# =======================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=api_key,
    temperature=0.3,
)

# =======================
# TOOL: OpenWeather
# =======================
def get_weather(city: str) -> str:
    """Get current weather for a city using OpenWeather API"""

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "en",
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
    except Exception:
        return f"❌ I couldn't get weather for **{city}**"

    data = r.json()

    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    desc = data["weather"][0]["description"].capitalize()
    wind = data["wind"]["speed"]
    city_name = data["name"]

    return (
        f"🌤 **Weather in {city_name}**\n"
        f"🌡 Temperature: {temp}°C (feels like {feels}°C)\n"
        f"☁ Condition: {desc}\n"
        f"💨 Wind: {wind} m/s"
    )

# =======================
# AGENT
# =======================
agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt=(
        "You are a weather assistant.\n"
        "When the user mentions a city or asks about weather, "
        "call the get_weather tool with the city name.\n"
        "Do NOT invent weather data."
    ),
)

# =======================
# TELEGRAM HANDLER
# =======================
async def handle(update, context):
    try:
        user_text = update.message.text

        result = agent.invoke({
            "messages": [
                {"role": "user", "content": user_text}
            ]
        })

        await update.message.reply_text(
            result["messages"][-1].content
        )

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("⚠️ Something went wrong. Try again.")

# =======================
# APP
# =======================
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🤖 Weather bot is running...")
app.run_polling()
