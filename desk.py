import asyncio
import random
import ssl
import json
import time
import uuid
import os
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

user_agent = UserAgent(os='windows', platforms='pc', browsers='chrome')
proxy_retry_limit = 5  # Batas maksimal percobaan ulang per proxy

# Fungsi untuk membuat folder trash jika belum ada
def create_trash_folder():
    trash_folder = "proxy_trash"
    if not os.path.exists(trash_folder):
        os.makedirs(trash_folder)
    return trash_folder

async def generate_random_user_agent():
    # Menghasilkan user-agent secara acak
    return user_agent.random

async def connect_to_wss(socks5_proxy, user_id, semaphore, proxy_failures):
    async with semaphore:
        retries = 0
        backoff = 0.5  # Kurangi nilai backoff awal untuk mempercepat rotasi

        device_id = str(uuid.uuid4())  # UUID yang acak tiap koneksi

        while retries < proxy_retry_limit:
            try:
                custom_headers = {
                    "User-Agent": await generate_random_user_agent(),
                    "Accept-Language": random.choice(["en-US", "en-GB", "id-ID"]),
                    "Referer": random.choice(["https://www.google.com/", "https://www.bing.com/"]),
                    "X-Forwarded-For": ".".join(map(str, (random.randint(1, 255) for _ in range(4)))),
                    "DNT": "1",  # Header tambahan untuk privasi
                    "Connection": "keep-alive"
                }
                logger.info(f"Connecting with device_id: {device_id}")

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                uri = random.choice(["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"])
                proxy = Proxy.from_url(socks5_proxy)

                async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname="proxy.wynd.network",
                                         extra_headers=custom_headers) as websocket:
                    
                    async def send_ping():
                        while True:
                            ping_message = json.dumps({
                                "id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}
                            })
                            logger.debug(f"Sending PING: {ping_message}")
                            await websocket.send(ping_message)
                            await asyncio.sleep(random.uniform(1, 3))  # Percepat interval PING menjadi 1-3 detik

                    asyncio.create_task(send_ping())

                    while True:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            message = json.loads(response)
                            logger.info(f"Received message: {message}")

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
                                logger.debug(f"Sending AUTH response: {auth_response}")
                                await websocket.send(json.dumps(auth_response))

                            elif message.get("action") == "PONG":
                                pong_response = {"id": message["id"], "origin_action": "PONG"}
                                logger.success("Successful", color="<green>")
                                await websocket.send(json.dumps(pong_response))

                        except asyncio.TimeoutError:
                            logger.warning("Reconnecting", color="<yellow>")
                            break

            except Exception as e:
                retries += 1
                logger.error("Failed", color="<red>")
                await asyncio.sleep(min(backoff, 2))  # Kurangi maksimum backoff menjadi 2 detik
                backoff *= 1.2  # Kurangi faktor peningkatan backoff untuk mempercepat rotasi

        if retries >= proxy_retry_limit:
            proxy_failures.append(socks5_proxy)
            logger.info(f"Proxy {socks5_proxy} telah dihapus setelah {proxy_retry_limit} percobaan.")

async def main():
    user_id = input("Masukkan user ID Anda: ")
    with open('local_proxies.txt', 'r') as file:
        local_proxies = file.read().splitlines()

    semaphore = asyncio.Semaphore(100)
    proxy_failures = []

    tasks = [connect_to_wss(proxy, user_id, semaphore, proxy_failures) for proxy in local_proxies]
    await asyncio.gather(*tasks)

    working_proxies = [proxy for proxy in local_proxies if proxy not in proxy_failures]

    # Tulis proxy yang berhasil ke 'local_proxies.txt'
    with open('local_proxies.txt', 'w') as file:
        file.write("\n".join(working_proxies))

    # Pindahkan proxy yang gagal ke folder trash dalam file proxy_trash.txt
    trash_folder = create_trash_folder()
    trash_file = os.path.join(trash_folder, "proxy_trash.txt")
    with open(trash_file, 'a') as file:
        file.write("\n".join(proxy_failures) + "\n")

    logger.info(f"Proses selesai. Proxy yang gagal telah dipindahkan ke {trash_file}.")

if __name__ == '__main__':
    asyncio.run(main())
