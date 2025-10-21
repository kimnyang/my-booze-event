from flask import Flask, render_template, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import threading
import time
import os
import subprocess
from flask_cors import CORS

# ===== Flask 기본 설정 =====
app = Flask(__name__)

# Cloudflare 전용 CORS 설정 (보안을 위해 특정 도메인만 허용)
CORS(app, resources={r"/*": {"origins": ["https://myboozeevent.com", "https://www.myboozeevent.com"]}})

# ===== 전역 변수 =====
price_data = []
time_data = []
current_price = 5000
lock = threading.Lock()
UPDATE_SECONDS = 300  # 5분 간격 (300초)
TZ = ZoneInfo("Asia/Seoul")  # ✅ 한국 시간대 적용

# ===== 함수 정의 =====
def now_kr():
    return datetime.now(TZ)

def is_market_open(now: datetime) -> bool:
    """장 운영 여부 (한국 시각 기준: 17시 ~ 익일 0시59분)"""
    hour = now.hour
    return (17 <= hour <= 23) or (hour == 0)

def should_reset_market(now: datetime) -> bool:
    """오후 5시에 자동 초기화 수행"""
    return now.hour == 17 and now.minute < 5  # 오후 5시 0~4분 사이

def price_simulator():
    global current_price, price_data, time_data
    last_reset_date = None

    while True:
        now = now_kr()

        # ✅ 장이 시작할 때 자동 초기화
        if should_reset_market(now) and last_reset_date != now.date():
            with lock:
                price_data.clear()
                time_data.clear()
                current_price = 5000
                price_data.append(current_price)
                time_data.append(now.strftime("%H:%M"))
                last_reset_date = now.date()
                print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 장 시작 - 데이터 초기화 완료")

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

# ===== 서버 시작 시 초기 데이터 설정 =====
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    with lock:
        if not price_data:
            price_data.append(current_price)
            time_data.append(now_kr().strftime("%H:%M"))
    threading.Thread(target=price_simulator, daemon=True).start()
    threading.Thread(target=start_tunnel, daemon=True).start()

# ===== 라우팅 =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    """프론트엔드에 가격 데이터 전달"""
    with lock:
        return jsonify({
            'timestamps': list(time_data),
            'prices': list(price_data),
            'market_open': is_market_open(now_kr()),
            'current_price': current_price
        })

# ===== 실행 =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
