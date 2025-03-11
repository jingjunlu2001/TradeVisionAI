from kafka import KafkaProducer
import requests
import json
import time
import os

API_KEY = os.getenv("AlphaVantage_API_Key")
symbol = "MSFT"

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
TOPIC_NAME = "alphavantage_intraday_api_data"

# Initialize Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

API_URL = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={API_KEY}'

def fetch_and_produce():
    while True:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            ts_data = data['Time Series (5min)']
            producer.send(TOPIC_NAME, ts_data)
            print(f"Sent data to Kafka: {ts_data}")
        else:
            print(f"API request failed: {response.status_code}")

        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    fetch_and_produce()
