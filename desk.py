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

async def generate_random_user_agent():
    return user_agent.random

async def connect_to_wss(socks5_proxy, user_id, semaphore):
    async with semaphore:
        retries = 0
        backoff = 1
        device_id = str(uuid.uuid4())

        while True:  # Loop tak terbatas sampai koneksi berhasil
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

                async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname="proxy.wynd.network",
                                         extra_headers=custom_headers) as websocket:
                    
                    async def send_ping():
                        while True:
                            ping_message = json.dumps({
                                "id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}
                            })
                            await websocket.send(ping_message)
                            await asyncio.sleep(random.uniform(2, 5))

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

                            elif message.get("action") == "PING":
                                pong_response = {"id": message["id"], "origin_action": "PING"}
                                await websocket.send(json.dumps(pong_response))

                        except asyncio.TimeoutError:
                            logger.warning("Reconnecting...")
                            break  # Kembali ke awal loop untuk mencoba ulang proxy yang sama

            except Exception as e:
                retries += 1
                logger.error(f"Failed to connect using proxy {socks5_proxy} (Retry {retries})")
                await asyncio.sleep(min(backoff, 5))
                backoff *= 1.5
                if retries >= proxy_retry_limit:
                    return False  # Mengembalikan status gagal untuk proxy ini

async def main():
    user_id = input("Masukkan user ID Anda: ")
    semaphore = asyncio.Semaphore(100)

    while True:
        proxy_failures = []
        
        # Load proxies from local_proxies.txt
        with open('local_proxies.txt', 'r') as file:
            local_proxies = file.read().splitlines()
        
        # Try to connect with local proxies first
        tasks = [connect_to_wss(proxy, user_id, semaphore) for proxy in local_proxies]
        results = await asyncio.gather(*tasks)
        
        # Check which proxies failed and add them to proxy_failures
        proxy_failures.extend([local_proxies[i] for i, success in enumerate(results) if not success])

        if proxy_failures:
            # Log proxies that failed
            with open('proxy_trash.txt', 'a') as file:
                file.write("\n".join(proxy_failures) + "\n")

            # Load proxies from proxy_trash.txt if all local proxies failed
            with open('proxy_trash.txt', 'r') as file:
                trash_proxies = file.read().splitlines()
            
            # Retry with proxies from proxy_trash.txt
            tasks = [connect_to_wss(proxy, user_id, semaphore) for proxy in trash_proxies]
            results = await asyncio.gather(*tasks)
            
            # Filter proxies that still failed after retrying
            proxy_failures = [trash_proxies[i] for i, success in enumerate(results) if not success]
        
        # Update local_proxies.txt with working proxies
        working_proxies = [proxy for proxy in local_proxies + trash_proxies if proxy not in proxy_failures]
        with open('local_proxies.txt', 'w') as file:
            file.write("\n".join(working_proxies))

        if not proxy_failures:
            logger.info("All proxies successfully connected.")
            break  # Stop if there are no more failed proxies to try again

if __name__ == '__main__':
    asyncio.run(main())
