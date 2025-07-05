from flask import Flask, render_template, request, send_file
import pandas as pd
import requests
from io import BytesIO
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

last_result_df = pd.DataFrame()

NSE_TICKERS = ["SBIN", "RELIANCE", "ICICIBANK", "TCS", "INFY", "HDFCBANK", "LT", "AXISBANK", "BHARTIARTL", "ITC"]

@app.route('/', methods=['GET', 'POST'])
def index():
    global last_result_df
    results = []

    if request.method == 'POST':
        dates = request.form.getlist('date')
        opens = request.form.getlist('open')
        highs = request.form.getlist('high')
        lows = request.form.getlist('low')
        closes = request.form.getlist('close')

        for i in range(len(dates)):
            o = float(opens[i])
            h = float(highs[i])
            l = float(lows[i])
            c = float(closes[i])
            signal = 'NEUTRAL'
            if o == h:
                signal = 'SELL'
            elif o == l:
                signal = 'BUY'
            results.append({
                'date': dates[i],
                'open': o,
                'high': h,
                'low': l,
                'close': c,
                'signal': signal
            })

        last_result_df = pd.DataFrame(results)

    return render_template('index.html', results=results, auto=False)

@app.route('/analyze')
def analyze():
    global last_result_df
    results = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive"
    })

    try:
        session.get("https://www.nseindia.com", timeout=5)
    except Exception as e:
        print("Failed to fetch NSE homepage for cookies:", e)

    for symbol in NSE_TICKERS:
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            r = session.get(url, timeout=5)
            if not r.ok or "priceInfo" not in r.text:
                raise ValueError("Invalid or blocked response")

            data = r.json()
            info = data['priceInfo']

            o = float(info['open'])
            h = float(info['intraDayHighLow']['max'])
            l = float(info['intraDayHighLow']['min'])
            c = float(info['lastPrice'])
            v = int(info['quantityTraded'])

            signal = 'NEUTRAL'
            if o == h:
                signal = 'SELL'
            elif o == l:
                signal = 'BUY'

            if signal != 'NEUTRAL':
                results.append({
                    'stock': symbol,
                    'open': o,
                    'high': h,
                    'low': l,
                    'close': c,
                    'volume': v,
                    'signal': signal
                })

            time.sleep(1)

        except Exception as e:
            print(f"Error with {symbol}: {e}")
            continue

    top5 = sorted(results, key=lambda x: x['volume'], reverse=True)[:5]
    last_result_df = pd.DataFrame(top5)
    return render_template('index.html', results=top5, auto=True)

@app.route('/download')
def download():
    global last_result_df
    if last_result_df.empty:
        return "No data to download.", 400

    csv_data = last_result_df.to_csv(index=False)
    buffer = BytesIO()
    buffer.write(csv_data.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='text/csv',
        download_name='ohl_strategy_results.csv',
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True)
