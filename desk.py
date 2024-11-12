async def connect_to_wss(socks5_proxy, user_id, semaphore, proxy_failures, working_proxies):
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

                async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname="proxy.wynd.network",
                                         extra_headers=custom_headers) as websocket:
                    
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
                                logger.success("Successful", color="<green>")
                                await websocket.send(json.dumps({"id": message["id"], "origin_action": "PONG"}))

                        except asyncio.TimeoutError:
                            logger.warning("Koneksi Ulang", color="<yellow>")
                            break

            except Exception as e:
                retries += 1
                logger.error("Gagal", color="<red>")
                await asyncio.sleep(min(backoff, 2)) 
                backoff *= 1.2  

        if retries >= proxy_retry_limit:
            proxy_failures.append(socks5_proxy)
            logger.info(f"Proxy {socks5_proxy} telah dihapus", color="<orange>")
        else:
            working_proxies.append(socks5_proxy)  # Simpan proxy yang berhasil ke daftar working_proxies

async def main():
    # Cek pembaruan skrip dari GitHub
    auto_update_script()
    
    # Periksa kode aktivasi sebelum melanjutkan
    check_activation_code()
    
    user_id = input("Masukkan user ID Anda: ")
    with open('local_proxies.txt', 'r') as file:
        local_proxies = file.read().splitlines()

    semaphore = asyncio.Semaphore(100)
    proxy_failures = []
    working_proxies = []  # Daftar proxy yang berhasil

    tasks = [connect_to_wss(proxy, user_id, semaphore, proxy_failures, working_proxies) for proxy in local_proxies]
    await asyncio.gather(*tasks)

    # Proses proxy yang gagal dengan cara mengulanginya
    if proxy_failures:
        logger.info("Mencoba ulang proxy yang gagal...")
        await asyncio.gather(*[connect_to_wss(proxy, user_id, semaphore, proxy_failures, working_proxies) for proxy in proxy_failures])

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
