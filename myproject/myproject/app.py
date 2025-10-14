from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import threading
import time
import os
import subprocess
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Cloudflare / 다른 출처에서 fetch 허용

# ===== 가격 데이터 & 동기화 =====
price_data = []
time_data = []
current_price = 5000
lock = threading.Lock()
UPDATE_SECONDS = 300  # 5분
TZ = ZoneInfo("Asia/Seoul")


def now_kr():
    return datetime.now(TZ)


def is_market_open(now: datetime) -> bool:
    """장 운영 여부 확인"""
    hour = now.hour
    return (17 <= hour <= 23) or (hour == 0)


def price_simulator():
    global current_price, price_data, time_data
    while True:
        now = now_kr()
        if is_market_open(now):
            last_price = current_price
            # 가격 규칙 (원래 로직 유지)
            if last_price >= 5000:
                change = -500 if random.random() < 0.48 else 0
            elif 3000 <= last_price < 4000:
                change = 500 if random.random() < 0.58 else -500
            elif last_price <= 2500:
                change = 500 if random.random() < 0.7 else 0
            else:
                change = random.choice([-500, 500])

            new_price = max(2500, min(5000, last_price + change))
            current_price = new_price
            timestamp = now.strftime("%H:%M")

            with lock:
                price_data.append(current_price)
                time_data.append(timestamp)
                if len(price_data) > 1000:
                    price_data.pop(0)
                    time_data.pop(0)

            print(f"[{now.strftime('%Y-%m-%d %H:%M')}] updated price -> {current_price}")
        else:
            print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 장 마감 - 업데이트 없음")

        time.sleep(UPDATE_SECONDS)


def start_tunnel():
    """Cloudflare Tunnel 자동 실행 (선택 사항). 실패해도 무시."""
    try:
        subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8080"])
    except Exception as e:
        print("Cloudflare Tunnel 실행 오류:", e)


# 서버 초기화: 싱가포르 시각으로 초기 타임스탬프 세팅
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    with lock:
        if not price_data:
            price_data.append(current_price)
            time_data.append(now_kr().strftime("%H:%M"))
    threading.Thread(target=price_simulator, daemon=True).start()
    # start_tunnel은 선택적(로컬에서 터널을 자동으로 띄우고 싶을 때)
    threading.Thread(target=start_tunnel, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def get_data():
    """/data : timestamps[], prices[], market_open (bool) — 모든 시간은 싱가포르 기준"""
    with lock:
        # 반환할 때 복사본을 내보내 안전성 확보
        return jsonify({
            'timestamps': list(time_data),
            'prices': list(price_data),
            'market_open': is_market_open(now_kr())
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host='0.0.0.0', port=port)