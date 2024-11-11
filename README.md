# BETA 

Penjelasan Perubahan

Peningkatan Semaphore: semaphore diatur ke 100, meningkatkan jumlah koneksi yang bisa berjalan secara paralel.

Interval Timeout Lebih Pendek: Timeout pada websocket.recv() diatur ke 5 detik untuk deteksi lebih cepat pada koneksi yang gagal.Ping

Interval Lebih Pendek: Interval pengiriman ping dikurangi menjadi 1-3 detik untuk menjaga koneksi tetap aktif tanpa harus menunggu lama.

Backoff Lebih Agresif: backoff maksimum dibatasi 2 detik dan bertambah secara lebih cepat, membuat koneksi ulang lebih responsif.

Fungsi create_trash_folder(): Membuat folder proxy_trash jika belum ada.

Pemindahan Proxy Gagal: Proxy yang gagal dipindahkan ke file failed_proxies_.txt di dalam folder proxy_trash, yang disimpan berdasarkan waktu (timestamp).

Log untuk Proxy Gagal: Setiap kali ada proxy gagal, file baru akan dibuat dalam folder proxy_trash, sehingga Anda memiliki rekaman yang mudah diakses tentang proxy yang bermasalah.
