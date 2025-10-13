from flask import Flask, render_template, jsonify
from datetime import datetime
import random
import threading
import time
import os

app = Flask(__name__)

price_data = []
time_data = []
current_price = 5000
lock = threading.Lock()

UPDATE_SECONDS = 300  # 5분


def is_market_open(now: datetime) -> bool:
    """장 운영 여부 확인 (17시 ~ 익일 0시59분)"""
    hour = now.hour
    return (17 <= hour <= 23) or (hour == 0)


def price_simulator():
    global current_price, price_data, time_data
    while True:
        now = datetime.now()
        if is_market_open(now):
            last_price = current_price
            # 가격 규칙
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

            print(f"[{now.strftime('%H:%M')}] updated price -> {current_price}")
        else:
            print(f"[{now.strftime('%H:%M')}] 장 마감 - 업데이트 없음")

        time.sleep(UPDATE_SECONDS)


# 서버 초기화
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    with lock:
        if not price_data:
            price_data.append(current_price)
            time_data.append(datetime.now().strftime("%H:%M"))

    threading.Thread(target=price_simulator, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def get_data():
    now = datetime.now()
    market_open = is_market_open(now)
    with lock:
        return jsonify({
            'timestamps': time_data,
            'prices': price_data,
            'market_open': market_open
        })


if __name__ == "__main__":
    # Render는 PORT 환경변수를 사용하므로 이렇게 수정
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host='0.0.0.0', port=port)