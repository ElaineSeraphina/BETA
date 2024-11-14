import asyncio
import random
import ssl
import json
import time
import uuid
import os
import gc
import sqlite3
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
from subprocess import call
from datetime import datetime
from typing import List

# Membaca konfigurasi dari file config.json
def load_config():
    if not os.path.exists('config.json'):
        logger.warning("File config.json tidak ditemukan, menggunakan nilai default.")
        return {
            "proxy_retry_limit": 5,
            "reload_interval": 60,
            "max_concurrent_connections": 50,
            "batch_size": 10,
            "rate_limit": 0.2
        }
    with open('config.json', 'r') as f:
        return json.load(f)

# Membuat folder data jika belum ada
if not os.path.exists('data'):
    os.makedirs('data')

# Setup SQLite untuk menyimpan proxy yang berhasil dan gagal
conn = sqlite3.connect('data/proxy_data.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS proxy_status (
                    proxy TEXT,
                    status TEXT,
                    last_checked TIMESTAMP)''')
conn.commit()

config = load_config()
proxy_retry_limit = config["proxy_retry_limit"]
reload_interval = config["reload_interval"]
max_concurrent_connections = config["max_concurrent_connections"]
batch_size = config["batch_size"]
rate_limit = config["rate_limit"]

user_agent = UserAgent(os='windows', platforms='pc', browsers='chrome')

# Fungsi pembaruan otomatis dari GitHub menggunakan API
def auto_update_script():
    update_choice = input("\033[91mApakah Anda ingin mengunduh data terbaru dari GitHub? (Y/N):\033[0m ")
    if update_choice.lower() == "y":
        logger.info("Memeriksa pembaruan skrip di GitHub...")
        if os.path.isdir(".git"):
            call(["git", "pull"])
            logger.info("Skrip diperbarui dari GitHub.")
        else:
            logger.warning("Repositori ini belum di-clone menggunakan git. Silakan clone menggunakan git untuk fitur auto-update.")
            exit()
    elif update_choice.lower() == "n":
        logger.info("Melanjutkan tanpa pembaruan.")
    else:
        logger.warning("Pilihan tidak valid. Program dihentikan.")
        exit()

# Fungsi untuk memeriksa kode aktivasi
def check_activation_code():
    while True:
        activation_code = input("Masukkan kode aktivasi: ")
        if activation_code == "UJICOBA":
            break
        else:
            print("Kode aktivasi salah! Silakan coba lagi.")

async def generate_random_user_agent():
    return user_agent.random

# Fungsi untuk menyimpan proxy ke database SQLite
def save_proxy_to_db(proxy, status):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO proxy_status (proxy, status, last_checked) VALUES (?, ?, ?)", (proxy, status, timestamp))
    conn.commit()

async def connect_to_wss(socks5_proxy, user_id, semaphore, proxy_failures):
    async with semaphore:
        retries = 0
        backoff = 0.5
        device_id = str(uuid.uuid4())

        while retries < proxy_retry_limit:
            try:
                custom_headers = {
                    "User-Agent": await generate_random_user_agent(),
                    "Accept-Language": random.choice(["en-US", "en-GB", "id-ID"]),
                    "Referer": random.choice(["https://www.google.com/", "https://www.bing.com/"]),
                    "X-Forwarded-For": ".".join(map(str, (random.randint(1, 255) for _ in range(4)))),
                    "DNT": "1",
                    "Connection": "keep-alive"
                }

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                uri = random.choice(["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"])
                proxy = Proxy.from_url(socks5_proxy)

                async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname="proxy.wynd.network", extra_headers=custom_headers) as websocket:

                    async def send_ping():
                        while True:
                            ping_message = json.dumps({
                                "id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}
                            })
                            await websocket.send(ping_message)
                            await asyncio.sleep(random.uniform(1, 3))

                    asyncio.create_task(send_ping())

                    while True:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            message = json.loads(response)

                            if message.get("action") == "AUTH":
                                auth_response = {
                                    "id": message["id"],
                                    "origin_action": "AUTH",
                                    "result": {
                                        "browser_id": device_id,
                                        "user_id": user_id,
                                        "user_agent": custom_headers['User-Agent'],
                                        "timestamp": int(time.time()),
                                        "device_type": "desktop",
                                        "version": "4.28.1",
                                    }
                                }
                                await websocket.send(json.dumps(auth_response))

                            elif message.get("action") == "PONG":
                                logger.success("BERHASIL")
                                await websocket.send(json.dumps({"id": message["id"], "origin_action": "PONG"}))

                        except asyncio.TimeoutError:
                            logger.warning("Koneksi Ulang")
                            break

            except Exception as e:
                retries += 1
                logger.error(f"ERROR: {e}")
                await asyncio.sleep(min(backoff, 2))
                backoff *= 1.2

        if retries >= proxy_retry_limit:
            proxy_failures.append(socks5_proxy)
            save_proxy_to_db(socks5_proxy, "failed")
            logger.info(f"Proxy {socks5_proxy} telah dihapus")

async def reload_proxy_list():
    while True:
        await asyncio.sleep(reload_interval)
        with open('local_proxies.txt', 'r') as file:
            local_proxies = file.read().splitlines()
        logger.info("Daftar proxy telah dimuat ulang.")
        return local_proxies

async def main():
    auto_update_script()
    check_activation_code()
    
    user_id = input("Masukkan user ID Anda: ")

    proxy_list_task = asyncio.create_task(reload_proxy_list())

    semaphore = asyncio.Semaphore(max_concurrent_connections)
    proxy_failures = []
    queue = asyncio.Queue()

    while True:
        local_proxies = await proxy_list_task
        for proxy in local_proxies:
            await queue.put(proxy)

        tasks = []
        for _ in range(batch_size):
            task = asyncio.create_task(process_proxy(queue, user_id, semaphore, proxy_failures))
            tasks.append(task)

        await asyncio.gather(*tasks)

        working_proxies = [proxy for proxy in local_proxies if proxy not in proxy_failures]
        with open('data/successful_proxies.txt', 'w') as file:
            file.write("\n".join(working_proxies))

        if not working_proxies:
            logger.info("Semua proxy gagal, menunggu untuk mencoba kembali...")
        else:
            logger.info(f"Proxy berhasil digunakan: {len(working_proxies)} proxy aktif.")

        await asyncio.sleep(reload_interval)

async def process_proxy(queue, user_id, semaphore, proxy_failures):
    while not queue.empty():
        socks5_proxy = await queue.get()
        await connect_to_wss(socks5_proxy, user_id, semaphore, proxy_failures)

if __name__ == "__main__":
    asyncio.run(main())
