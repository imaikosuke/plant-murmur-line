from fastapi import FastAPI, Request, HTTPException
from openai import OpenAI
import requests
from dotenv import load_dotenv
import os
import logging

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数の取得
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# OpenAIクライアントの設定
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
def read_root():
    return {"message": "FastAPI server is running successfully!"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received request body: {body}")

        # LINE Messaging APIからのリクエストを検証
        if 'events' not in body or not body['events']:
            logger.warning("Received empty events list")
            return {"status": "ok"}

        event = body['events'][0]
        if event['type'] != 'message' or event['message']['type'] != 'text':
            logger.error("Invalid event type")
            raise HTTPException(status_code=400, detail="Invalid event type")

        user_message = event['message']['text']
        logger.info(f"Received message: {user_message}")

        # OpenAI APIを使用して植物との会話を生成
        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはユーザーが持ち主の植物です。植物が可愛く話すかのように返信してください。"},
                    {"role": "user", "content": user_message}
                ]
            )
            plant_response = completion.choices[0].message.content
            logger.info(f"Generated response: {plant_response}")
        except:
            plant_response = "Zzz..."
            logger.info(f"Generated response: {plant_response}")

        # LINEに応答を送信
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
        }
        reply_message = {
            "replyToken": event['replyToken'],
            "messages": [{"type": "text", "text": plant_response}]
        }
        response = requests.post('https://api.line.me/v2/bot/message/reply', headers=headers, json=reply_message)
        logger.info(f"Reply sent, status code: {response.status_code}, response: {response.text}")

        if response.status_code != 200:
            logger.error(f"Error sending reply: {response.status_code}, {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
