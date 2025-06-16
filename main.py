from fastapi import FastAPI, Request, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from playwright.async_api import async_playwright
import uuid, os, aiohttp
from flask import Flask, request as flask_request
from handlers.download import handle_download
from handlers.response import send_message
from handlers.welcome import send_welcome
from handlers.donate import send_donate_options
import logging, uvicorn

flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = flask_request.json
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")
    if text == "/start":
        send_welcome(chat_id)
    elif text.lower() in ["/donate", "донат", "поддержать"]:
        send_donate_options(chat_id)
    elif "http" in text:
        send_message(chat_id, "🎬 Скачиваю видео...")
        handle_download(chat_id, text)
    else:
        send_message(chat_id, "Отправь ссылку на видео")
    return {"ok": True}

@flask_app.route("/")
def home():
    return "Bot is running"

app = FastAPI()
app.mount("/", WSGIMiddleware(flask_app))

@app.get("/download")
async def download_video(url: str = Query(...)):
    if not url.startswith("https://www.instagram.com/reels/"):
        return JSONResponse(content={"error": "Неверный формат URL"}, status_code=400)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_selector("video", timeout=10000)
            video_url = await page.eval_on_selector("video", "el => el.src")
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    content = await response.read()
            filename = f"/tmp/{uuid.uuid4()}.mp4"
            with open(filename, "wb") as f:
                f.write(content)
            await browser.close()
            return FileResponse(filename, media_type="video/mp4", filename="insta.mp4")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
