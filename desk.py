import random
import requests
import time
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed
import smtplib
from email.mime.text import MIMEText
import aiohttp
import asyncio

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Daftar proxy untuk digunakan
proxies = ['proxy1', 'proxy2', 'proxy3']  # Ganti dengan daftar proxy yang benar

# Fitur 1: Rotasi Proxy yang Lebih Cerdas
def rotate_proxy(proxies):
    batch_size = 10
    selected_proxies = random.sample(proxies, batch_size)
    return selected_proxies

# Fitur 2: Retry Logic dengan Tenacity
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def make_request(proxy):
    response = requests.get('http://example.com', proxies={"http": proxy}, timeout=10)
    return response

# Penanganan Kesalahan dengan Logging
def make_request_with_logging(proxy):
    try:
        response = make_request(proxy)
        return response
    except Exception as e:
        logging.error(f"Error while making request with proxy {proxy}: {str(e)}")
        return None

# Fitur 1: Pengelolaan Batching Proxy
def process_proxies_in_batches(proxies):
    batch_size = 10
    batches = [proxies[i:i + batch_size] for i in range(0, len(proxies), batch_size)]
    
    for batch in batches:
        results = [make_request_with_logging(proxy) for proxy in batch]
        process_results(results)

# Placeholder for processing results (tambahkan sesuai kebutuhan)
def process_results(results):
    for result in results:
        if result:
            logging.info(f"Request successful with response: {result.status_code}")
        else:
            logging.warning("Request failed.")

# Fitur 4: Pengaturan Timeout dan Pemberitahuan Waktu Berjalan Lama
def process_request_with_timeout(proxy):
    start_time = time.time()
    response = requests.get('http://example.com', proxies={"http": proxy}, timeout=10)
    end_time = time.time()
    
    if end_time - start_time > 5:
        logging.warning(f"Request with proxy {proxy} took longer than expected.")
    
    return response

# Fitur 5: Pembaruan Skrip secara Otomatis menggunakan Git
def update_script():
    try:
        subprocess.run(["git", "pull"], check=True)
        logging.info("Script updated successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update script: {e}")

# Fitur 5: Pembaruan Dependensi dengan Pip
def update_dependencies():
    try:
        subprocess.run(["pip", "install", "--upgrade", "requests"], check=True)
        logging.info("Dependencies updated successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update dependencies: {e}")

# Fitur 6: Penggunaan Multi-threading untuk Proses Paralel
def process_proxy(proxy):
    response = make_request_with_logging(proxy)
    return response

def process_proxies_parallel(proxies):
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_proxy, proxies))
    return results

# Fitur 7: Notifikasi Melalui Email
def send_email(subject, body, to_email):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'your-email@example.com'   # Ganti dengan email pengirim
    msg['To'] = to_email
    
    try:
        with smtplib.SMTP('smtp.example.com') as server:  # Ganti dengan SMTP server yang kamu gunakan
            server.login('your-email@example.com', 'your-password')  # Ganti dengan login dan password email kamu
            server.sendmail('your-email@example.com', to_email, msg.as_string())
        logging.info(f"Notification email sent to {to_email}.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

# Fitur 8: Aiohttp untuk HTTP Non-Blocking
async def fetch_url(url, session):
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        logging.error(f"Failed to fetch URL {url}: {e}")
        return None

async def process_urls_async(proxies):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(f'http://example.com/{proxy}', session) for proxy in proxies]
        html_pages = await asyncio.gather(*tasks)
        logging.info("Asynchronous fetching completed.")
        return html_pages

# Contoh Pemakaian Skrip Utama
if __name__ == "__main__":
    rotated_proxies = rotate_proxy(proxies)
    process_proxies_in_batches(rotated_proxies)
    
    update_script()
    update_dependencies()
    
    send_email("Script Update", "Script has been updated successfully.", "recipient@example.com")  # Ganti dengan email penerima
    
    # Process proxies in parallel
    results = process_proxies_parallel(proxies)
    logging.info("Parallel processing completed.")

    # Menjalankan Async
    asyncio.run(process_urls_async(proxies))
