import requests
import os
import time

# Fungsi untuk memuat proxy dari file
def load_proxies(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

# Fungsi untuk mencoba permintaan dengan proxy
def make_request(url, proxy):
    try:
        response = requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=5)
        response.raise_for_status()  # Raise error untuk status buruk
        print(f"Sukses dengan proxy: {proxy}")
        return response
    except requests.RequestException as e:
        print(f"Gagal dengan proxy: {proxy} - {e}")
        return None

# Fungsi utama untuk mencoba ulang hingga berhasil atau pengguna menghentikan
def run_script():
    url = "http://example.com"
    main_proxy = "http://18.141.205.147:8080"
    trash_proxies_path = "trash_proxies/proxies.txt"  # Sesuaikan path file di folder `trash proxies`

    # Coba ulang terus hingga ada yang berhasil atau pengguna menghentikan
    while True:
        # Muat proxy cadangan dari folder `trash proxies`
        backup_proxies = load_proxies(trash_proxies_path)
        
        # Coba permintaan dengan proxy utama
        response = make_request(url, main_proxy)

        # Jika proxy utama gagal, coba dengan proxy dari `trash proxies`
        if response is None:
            for backup_proxy in backup_proxies:
                response = make_request(url, backup_proxy)
                if response:
                    break  # Berhenti jika berhasil

        # Jika masih gagal dengan semua proxy, tunggu beberapa detik sebelum mencoba ulang
        if response:
            print("Permintaan berhasil dilakukan.")
            break
        else:
            print("Semua proxy gagal. Menunggu 10 detik sebelum mencoba ulang...")
            time.sleep(10)  # Tunggu 10 detik sebelum mencoba ulang
            print("Mengulangi proses dengan proxy dari folder `trash proxies`...")

# Menjalankan script
run_script()
