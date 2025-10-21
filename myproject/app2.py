from flask import Flask, render_template, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import threading
import time
import subprocess
import os

# ===== Flask 기본 설정 =====
app = Flask(__name__)

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
    """장이 열리는 시간 (한국 시각 기준: 17시 ~ 익일 0시59분)"""
    hour = now.hour
    return (17 <= hour <= 23) or (hour == 0)

def should_reset_market(now: datetime) -> bool:
    """오후 4시 30분 ~ 4시 34분 사이에 초기화"""
    return now.hour == 16 and 30 <= now.minute < 35

def price_simulator():
    global current_price, price_data, time_data
    last_reset_date = None

    while True:
        now = now_kr()

        # ✅ 오후 4시 30분에 초기화 (단 하루 1번만)
        if should_reset_market(now) and last_reset_date != now.date():
            with lock:
                price_data.clear()
                time_data.clear()
                current_price = 5000
                price_data.append(current_price)
                time_data.append(now.strftime("%H:%M"))
                last_reset_date = now.date()
                print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 데이터 초기화 완료")

        # ✅ 장이 열리는 시간에만 가격 갱신
        if is_market_open(now):
            last_price = current_price

            # 가격 변화 규칙
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

            print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 가격 갱신 → {current_price}")
        else:
            print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 장 마감 - 업데이트 없음")

        time.sleep(UPDATE_SECONDS)

def start_cloudflare_tunnel():
    """✅ Cloudflare Tunnel을 자동으로 실행"""
    try:
        print("🌐 Cloudflare Tunnel 시작 중...")
        subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8080"])
    except Exception as e:
        print("❌ Cloudflare Tunnel 실행 오류:", e)

# ===== 서버 시작 시 초기 데이터 설정 =====
if not app.debug or os.environ.get("WERKJERG_RUN_MAIN") == "true":
    with lock:
        if not price_data:
            price_data.append(current_price)
            time_data.append(now_kr().strftime("%H:%M"))
    threading.Thread(target=price_simulator, daemon=True).start()
    threading.Thread(target=start_cloudflare_tunnel, daemon=True).start()

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
    app.run(debug=False, host='0.0.0.0', port=8080)