import psycopg2

# ===== VARIABEL TETAP (KONSTANTA) =====
BATAS_AIR = 3000              # maksimal air per hari (ml)
TARGET_AWAL = 2000            # target awal minum per hari (ml)
MIN_SANDI = 3                 # panjang minimal kata sandi
MAKS_SANDI = 6                # panjang maksimal kata sandi
MAKS_TIDUR = 6 * 60           # durasi tidur maksimal yang dicatat (menit)
BATAS_KURANG_TIDUR = 5 * 60   # di bawah ini = kurang tidur (menit)

# ===== VARIABEL PENYIMPAN DATA SEMENTARA =====
# Dictionary dipakai supaya isinya bisa diubah dari dalam def
# (id = 0 artinya belum ada orang yang dipilih / belum login)
akun = {"id": 0, "nama": "", "username": "", "target": 0, "role": ""}   # user yang sedang login
sasaran = {"id": 0, "nama": ""}   # user yang datanya sedang ditampilkan (diri sendiri atau anak)

# ===== KONEKSI DATABASE =====
try:
    db = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",         # ganti sesuai user PostgreSQL kamu
        password="54321",        # ganti dengan password PostgreSQL kamu
        dbname="db_sleepyhydrate"
    )
    db.autocommit = True         # setiap perintah langsung tersimpan
    cur = db.cursor()            # cursor = "pena" untuk menjalankan perintah SQL
    terhubung = True
except psycopg2.Error as error:
    print("Gagal terhubung ke database:", error)
    terhubung = False


# =====================================================
#  BAGIAN 1 : PERSIAPAN DATABASE
# =====================================================
def siapkan_database():
    # tambah kolom id_ortu kalau belum ada
    cur.execute("ALTER TABLE pengguna ADD COLUMN IF NOT EXISTS id_ortu INTEGER")

    # pastikan role "orangtua" dan "anak" sudah ada di tabel role
    for nama_role in ["orangtua", "anak"]:
        cur.execute("SELECT id_role FROM role WHERE nama_role = %s", (nama_role,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO role (nama_role) VALUES (%s)", (nama_role,))


# =====================================================
#  BAGIAN 2 : REGISTRASI & LOGIN
# =====================================================
def muat_akun():
    # ambil ulang data akun yang sedang login dari database
    cur.execute(
        "SELECT p.nama_pengguna, p.username, p.target_harian, r.nama_role "
        "FROM pengguna p JOIN role r ON p.id_role = r.id_role "
        "WHERE p.id_pengguna = %s", (akun["id"],)
    )
    data = cur.fetchone()      # data = tuple, urutannya sama seperti SELECT
    akun["nama"] = data[0]
    akun["username"] = data[1]
    akun["target"] = data[2]
    akun["role"] = data[3]


def buat_akun():
    # Dipakai 2 tempat:
    # - belum login (akun["id"] == 0)  -> registrasi orang tua
    # - orang tua sudah login          -> tambah akun anak
    if akun["id"] == 0:
        role = "orangtua"
        id_ortu = None
        print("--- REGISTRASI ORANG TUA ---")
    else:
        role = "anak"
        id_ortu = akun["id"]
        print("--- TAMBAH AKUN ANAK ---")

    nama = input("Nama lengkap : ")
    username = input("Username     : ")
    sandi = input(f"Kata sandi ({MIN_SANDI}-{MAKS_SANDI} karakter) : ")

    # cek apakah nama / username sudah dipakai
    cur.execute("SELECT id_pengguna FROM pengguna WHERE nama_pengguna = %s", (nama,))
    nama_dipakai = cur.fetchone() is not None
    cur.execute("SELECT id_pengguna FROM pengguna WHERE username = %s", (username,))
    username_dipakai = cur.fetchone() is not None

    if nama == "" or username == "" or sandi == "":
        print("Semua data wajib diisi!")
    elif len(sandi) < MIN_SANDI or len(sandi) > MAKS_SANDI:
        print(f"Kata sandi harus {MIN_SANDI} sampai {MAKS_SANDI} karakter!")
    elif nama_dipakai:
        print("Nama sudah dipakai, gunakan nama yang berbeda!")
    elif username_dipakai:
        print("Username sudah dipakai, gunakan username lain!")
    else:
        # kolom id tidak auto-increment, jadi nomor berikutnya dicari manual
        cur.execute("SELECT COALESCE(MAX(id_pengguna), 0) + 1 FROM pengguna")
        id_baru = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO pengguna (id_pengguna, id_role, nama_pengguna, username, password, target_harian, id_ortu) "
            "VALUES (%s, (SELECT id_role FROM role WHERE nama_role = %s), %s, %s, %s, %s, %s)",
            (id_baru, role, nama, username, sandi, TARGET_AWAL, id_ortu)
        )
        if role == "orangtua":
            print("Registrasi berhasil! Silakan login.")
        else:
            print("Akun anak berhasil dibuat.")


def login():
    print("--- LOGIN ---")
    username = input("Username    : ")
    sandi = input("Kata sandi : ")

    cur.execute(
        "SELECT id_pengguna FROM pengguna WHERE username = %s AND password = %s",
        (username, sandi)
    )
    data = cur.fetchone()      # None kalau tidak ada yang cocok

    if data is None:
        print("Username atau kata sandi salah!")
    else:
        akun["id"] = data[0]
        muat_akun()
        print(f"Login berhasil. Selamat datang, {akun['nama']}!")


def menu_awal():
    while True:
        print("\n==============================")
        print("        SLEEPYHYDRATE")
        print("==============================")
        print("1. Registrasi (Orang tua)")
        print("2. Login")
        print("3. Selesai")
        pilihan = input("Pilih menu: ")

        match pilihan:
            case "1":
                buat_akun()
            case "2":
                login()
                if akun["id"] != 0:
                    menu_utama()
            case "3":
                print("Terima kasih sudah memakai SleepyHydrate. Tetap sehat!")
                break
            case _:
                print("Pilihan tidak valid!")


def menu_utama():
    while akun["id"] != 0:
        # menu catatan & korelasi selalu menampilkan data diri sendiri
        sasaran["id"] = akun["id"]
        sasaran["nama"] = akun["nama"]

        print(f"\n=== MENU UTAMA ({akun['nama']} - {akun['role']}) ===")
        print("1. Akun")
        print("2. Catatan Tidur")
        print("3. Catatan Minum")
        print("4. Korelasi Kesehatan")
        if akun["role"] == "orangtua":
            print("5. Pantau Anak")
        print("0. Logout")
        pilihan = input("Pilih menu: ")

        match pilihan:
            case "1":
                menu_akun()
            case "2":
                menu_tidur()
            case "3":
                menu_minum()
            case "4":
                korelasi()
            case "5" if akun["role"] == "orangtua":
                menu_pantau_anak()
            case "0":
                akun["id"] = 0
                print("Kamu sudah logout.")
            case _:
                print("Pilihan tidak valid!")


# =====================================================
#  BAGIAN 3 : AKUN
# =====================================================
def lihat_profil():
    muat_akun()
    print("\n--- PROFIL ---")
    print("Nama         :", akun["nama"])
    print("Username     :", akun["username"])
    print("Peran        :", akun["role"])
    print("Target minum :", akun["target"], "ml/hari")


def edit_profil():
    print("--- EDIT PROFIL (kosongkan jika tidak diubah) ---")
    nama_baru = input("Nama baru       : ")
    username_baru = input("Username baru   : ")
    sandi_baru = input(f"Kata sandi baru ({MIN_SANDI}-{MAKS_SANDI} karakter) : ")

    if nama_baru != "":
        cur.execute("SELECT id_pengguna FROM pengguna WHERE nama_pengguna = %s", (nama_baru,))
        if cur.fetchone() is None:
            cur.execute("UPDATE pengguna SET nama_pengguna = %s WHERE id_pengguna = %s",
                        (nama_baru, akun["id"]))
        else:
            print("Nama itu sudah dipakai, nama tidak diubah.")

    if username_baru != "":
        cur.execute("SELECT id_pengguna FROM pengguna WHERE username = %s", (username_baru,))
        if cur.fetchone() is None:
            cur.execute("UPDATE pengguna SET username = %s WHERE id_pengguna = %s",
                        (username_baru, akun["id"]))
        else:
            print("Username itu sudah dipakai, username tidak diubah.")

    if sandi_baru != "":
        if len(sandi_baru) >= MIN_SANDI and len(sandi_baru) <= MAKS_SANDI:
            cur.execute("UPDATE pengguna SET password = %s WHERE id_pengguna = %s",
                        (sandi_baru, akun["id"]))
        else:
            print(f"Kata sandi harus {MIN_SANDI} sampai {MAKS_SANDI} karakter, kata sandi tidak diubah.")

    print("Proses edit profil selesai.")


def hapus_pengguna():
    # Menghapus "sasaran" beserta catatannya.
    # Kalau sasaran adalah orang tua, semua anaknya (id_ortu = id sasaran) ikut terhapus.
    cur.execute(
        "DELETE FROM catatan_tidur WHERE id_pengguna IN "
        "(SELECT id_pengguna FROM pengguna WHERE id_ortu = %s OR id_pengguna = %s)",
        (sasaran["id"], sasaran["id"])
    )
    cur.execute(
        "DELETE FROM catatan_minum WHERE id_pengguna IN "
        "(SELECT id_pengguna FROM pengguna WHERE id_ortu = %s OR id_pengguna = %s)",
        (sasaran["id"], sasaran["id"])
    )
    cur.execute(
        "DELETE FROM pengguna WHERE id_ortu = %s OR id_pengguna = %s",
        (sasaran["id"], sasaran["id"])
    )


def hapus_akun():
    if akun["role"] == "orangtua":
        print("PERINGATAN: menghapus akun orang tua juga menghapus SEMUA akun anak.")
    yakin = input("Yakin menghapus akun? Ketik ya untuk lanjut: ").lower()

    if yakin == "ya":
        sasaran["id"] = akun["id"]
        hapus_pengguna()
        akun["id"] = 0           # 0 = otomatis logout
        print("Akun berhasil dihapus.")
    else:
        print("Penghapusan dibatalkan.")


def menu_akun():
    while akun["id"] != 0:       # kalau akun terhapus, loop otomatis berhenti
        lihat_profil()
        print("\n1. Edit profil")
        print("2. Hapus akun")
        print("0. Kembali")
        pilihan = input("Pilih menu: ")

        match pilihan:
            case "1":
                edit_profil()
            case "2":
                hapus_akun()
            case "0":
                break
            case _:
                print("Pilihan tidak valid!")


# =====================================================
#  BAGIAN 4 : CATATAN TIDUR
# =====================================================
def mulai_tidur():
    cur.execute(
        "SELECT id_tidur FROM catatan_tidur WHERE id_pengguna = %s AND waktu_bangun IS NULL",
        (akun["id"],)
    )
    if cur.fetchone() is not None:
        print("Kamu masih tercatat tidur. Pilih 'Bangun tidur' dulu!")
    else:
        cur.execute("SELECT COALESCE(MAX(id_tidur), 0) + 1 FROM catatan_tidur")
        id_baru = cur.fetchone()[0]
        # tanggal & jam diambil dari server database (CURRENT_DATE dan LOCALTIME)
        cur.execute(
            "INSERT INTO catatan_tidur (id_tidur, id_pengguna, tanggal, waktu_tidur) "
            "VALUES (%s, %s, CURRENT_DATE, LOCALTIME(0)) RETURNING waktu_tidur",
            (id_baru, akun["id"])
        )
        jam = cur.fetchone()[0]
        print("Waktu mulai tidur dicatat:", jam)
        print("Selamat tidur!")


def bangun_tidur():
    # database yang menghitung selisih waktu sekarang - waktu mulai tidur (hasil dalam menit)
    cur.execute(
        "SELECT id_tidur, EXTRACT(EPOCH FROM (LOCALTIMESTAMP - (tanggal + waktu_tidur))) / 60 "
        "FROM catatan_tidur WHERE id_pengguna = %s AND waktu_bangun IS NULL "
        "ORDER BY id_tidur DESC",
        (akun["id"],)
    )
    data = cur.fetchone()

    if data is None:
        print("Belum ada catatan mulai tidur. Pilih 'Mulai tidur' dulu!")
    else:
        id_tidur = data[0]
        menit = int(data[1])

        # batasi durasi tidur maksimal
        if menit > MAKS_TIDUR:
            menit = MAKS_TIDUR
            print(f"Durasi tidur dibatasi maksimal {MAKS_TIDUR // 60} jam.")

        # 1. tampilkan durasi tidur
        print("Selamat pagi! Kamu tidur selama", menit // 60, "jam", menit % 60, "menit")

        # 2. peringatan kalau kurang tidur
        if menit < BATAS_KURANG_TIDUR:
            print("\n!!! KURANG TIDUR !!!")
            print(f"Kamu tidur kurang dari {BATAS_KURANG_TIDUR // 60} jam. Usahakan tidur lebih cukup malam ini.")

        # 3. tanya kondisi tubuh, ulangi sampai jawabannya valid
        kebugaran = ""
        while kebugaran == "":
            print("\nBagaimana kondisi tubuhmu sekarang?")
            print("1. Segar")
            print("2. Pusing")
            print("3. Lemas")
            pilihan = input("Pilih (1-3): ")

            match pilihan:
                case "1":
                    kebugaran = "segar"
                case "2":
                    kebugaran = "pusing"
                case "3":
                    kebugaran = "lemas"
                case _:
                    print("Pilihan tidak valid!")

        cur.execute(
            "UPDATE catatan_tidur SET waktu_bangun = LOCALTIME(0), durasi_tidur = %s, kebugaran = %s "
            "WHERE id_tidur = %s",
            (menit, kebugaran, id_tidur)
        )
        print("\nKondisi tubuh:", kebugaran)
        print("Catatan tidur berhasil disimpan.")


def riwayat_tidur():
    cur.execute(
        "SELECT tanggal, waktu_tidur, waktu_bangun, durasi_tidur, kebugaran "
        "FROM catatan_tidur WHERE id_pengguna = %s ORDER BY id_tidur DESC LIMIT 7",
        (sasaran["id"],)
    )
    data = cur.fetchall()      # data = list berisi tuple

    if len(data) == 0:
        print("Belum ada catatan tidur.")
    else:
        print("\n--- RIWAYAT TIDUR (7 terakhir) ---")
        for d in data:
            # urutan isi d: 0 tanggal, 1 waktu_tidur, 2 waktu_bangun, 3 durasi (menit), 4 kebugaran
            if d[2] is None:
                print(f"{d[0]} | tidur {d[1]} | (masih tidur)")
            else:
                baris = f"{d[0]} | tidur {d[1]} | bangun {d[2]} | {d[3] // 60} jam {d[3] % 60} menit | {d[4]}"
                if d[3] < BATAS_KURANG_TIDUR:
                    baris += " | ** KURANG TIDUR **"
                print(baris)


def menu_tidur():
    while True:
        print("\n=== CATATAN TIDUR ===")
        print("1. Mulai tidur")
        print("2. Bangun tidur")
        print("3. Riwayat tidur")
        print("0. Kembali")
        pilihan = input("Pilih menu: ")

        match pilihan:
            case "1":
                mulai_tidur()
            case "2":
                bangun_tidur()
            case "3":
                riwayat_tidur()
            case "0":
                break
            case _:
                print("Pilihan tidak valid!")


# =====================================================
#  BAGIAN 5 : CATATAN MINUM
# =====================================================
def tampilkan_progress():
    cur.execute("SELECT target_harian FROM pengguna WHERE id_pengguna = %s", (sasaran["id"],))
    target = cur.fetchone()[0]
    cur.execute(
        "SELECT COALESCE(SUM(jumlah_air), 0) FROM catatan_minum "
        "WHERE id_pengguna = %s AND tanggal = CURRENT_DATE",
        (sasaran["id"],)
    )
    total = int(cur.fetchone()[0])

    persen = total / target * 100
    if persen > 100:
        persen = 100
    blok = int(persen / 5)                    # 20 blok = 100%
    bar = "#" * blok + "-" * (20 - blok)
    print(f"[{bar}] {int(persen)}%  ({total} / {target} ml)")
    if total >= target:
        print("Target hari ini sudah tercapai. Hebat!")


def tambah_minum():
    cur.execute(
        "SELECT COALESCE(SUM(jumlah_air), 0) FROM catatan_minum "
        "WHERE id_pengguna = %s AND tanggal = CURRENT_DATE",
        (akun["id"],)
    )
    sisa = BATAS_AIR - int(cur.fetchone()[0])

    if sisa <= 0:
        print("Batas input air hari ini (3 liter) sudah tercapai!")
    else:
        print("Pilih jumlah air yang diminum:")
        print("1. 250 ml (1 gelas)")
        print("2. 500 ml (1 botol kecil)")
        print("3. Isi sendiri")
        pilihan = input("Pilih (1-3): ")

        jumlah = 0               # 0 = belum ada jumlah yang valid
        match pilihan:
            case "1":
                jumlah = 250
            case "2":
                jumlah = 500
            case "3":
                isi = input("Jumlah air (ml): ")
                if isi.isdigit() and int(isi) > 0:
                    jumlah = int(isi)
                else:
                    print("Jumlah harus berupa angka lebih dari 0!")
            case _:
                print("Pilihan tidak valid!")

        if jumlah > sisa:
            print(f"Melebihi batas! Kamu hanya bisa menambah maksimal {sisa} ml lagi hari ini.")
        elif jumlah > 0:
            cur.execute(
                "INSERT INTO catatan_minum (id_pengguna, tanggal, jumlah_air, waktu_minum) "
                "VALUES (%s, CURRENT_DATE, %s, LOCALTIME(0))",
                (akun["id"], jumlah)
            )
            print(f"Berhasil mencatat {jumlah} ml.")


def riwayat_minum():
    cur.execute(
        "SELECT waktu_minum, jumlah_air FROM catatan_minum "
        "WHERE id_pengguna = %s AND tanggal = CURRENT_DATE ORDER BY waktu_minum",
        (akun["id"],)
    )
    data = cur.fetchall()

    if len(data) == 0:
        print("Belum ada catatan minum hari ini.")
    else:
        print("--- RIWAYAT MINUM HARI INI ---")
        for d in data:
            print(f"{d[0]} | {d[1]} ml")


def atur_target():
    # mengatur target minum milik "sasaran" (diri sendiri atau anak)
    isi = input(f"Target baru (500 - {BATAS_AIR} ml): ")
    if isi.isdigit() and 500 <= int(isi) <= BATAS_AIR:
        cur.execute("UPDATE pengguna SET target_harian = %s WHERE id_pengguna = %s",
                    (int(isi), sasaran["id"]))
        print("Target minum berhasil diubah menjadi", isi, "ml.")
    else:
        print(f"Target harus berupa angka antara 500 sampai {BATAS_AIR}!")


def menu_minum():
    while True:
        print("\n=== CATATAN MINUM ===")
        tampilkan_progress()
        print("\n1. Tambah minum")
        print("2. Lihat riwayat hari ini")
        if akun["role"] == "orangtua":
            print("3. Atur target harian")
        print("0. Kembali")
        pilihan = input("Pilih menu: ")

        match pilihan:
            case "1":
                tambah_minum()
            case "2":
                riwayat_minum()
            case "3" if akun["role"] == "orangtua":
                atur_target()
            case "0":
                break
            case _:
                print("Pilihan tidak valid!")


# =====================================================
#  BAGIAN 6 : KORELASI KESEHATAN
# =====================================================
def korelasi():
    cur.execute(
        "SELECT t.tanggal, t.durasi_tidur, t.kebugaran, "
        "COALESCE((SELECT SUM(m.jumlah_air) FROM catatan_minum m "
        "          WHERE m.id_pengguna = t.id_pengguna AND m.tanggal = t.tanggal), 0) "
        "FROM catatan_tidur t "
        "WHERE t.id_pengguna = %s AND t.kebugaran IS NOT NULL "
        "ORDER BY t.tanggal",
        (sasaran["id"],)
    )
    data = cur.fetchall()
    # urutan isi d: 0 tanggal, 1 durasi tidur (menit), 2 kebugaran, 3 total air (ml)

    print(f"=== KORELASI KESEHATAN: {sasaran['nama']} ===")
    if len(data) == 0:
        print("Belum ada data lengkap (tidur + kebugaran) untuk dianalisis.")
    else:
        # 1. tabel data
        print("\nTanggal | Tidur | Air | Kondisi")
        for d in data:
            print(f"{d[0]} | {d[1] // 60} jam {d[1] % 60} menit | {int(d[3])} ml | {d[2]}")

        # 2. grafik sederhana durasi tidur (1 # = 1 jam)
        print("\nGrafik durasi tidur (1 # = 1 jam):")
        for d in data:
            print(f"{d[0]} | {'#' * (d[1] // 60)} {d[1] // 60} jam")

        # 3. hitung jumlah hari, total tidur, dan total air untuk tiap kondisi
        jumlah = {"segar": 0, "pusing": 0, "lemas": 0}
        total_tidur = {"segar": 0, "pusing": 0, "lemas": 0}
        total_air = {"segar": 0, "pusing": 0, "lemas": 0}
        for d in data:
            kondisi = d[2]
            jumlah[kondisi] += 1
            total_tidur[kondisi] += d[1]
            total_air[kondisi] += int(d[3])

        print("\nRata-rata berdasarkan kondisi tubuh:")
        for kondisi in jumlah:
            if jumlah[kondisi] > 0:
                rata_tidur = int(total_tidur[kondisi] / jumlah[kondisi])
                rata_air = int(total_air[kondisi] / jumlah[kondisi])
                print(f"- {kondisi}: tidur {rata_tidur // 60} jam {rata_tidur % 60} menit, "
                      f"air {rata_air} ml ({jumlah[kondisi]} hari)")

        # 4. kesimpulan: bandingkan hari segar dengan hari tidak segar (pusing + lemas)
        hari_lain = jumlah["pusing"] + jumlah["lemas"]
        if jumlah["segar"] > 0 and hari_lain > 0:
            tidur_segar = total_tidur["segar"] / jumlah["segar"]
            tidur_lain = (total_tidur["pusing"] + total_tidur["lemas"]) / hari_lain
            air_segar = total_air["segar"] / jumlah["segar"]
            air_lain = (total_air["pusing"] + total_air["lemas"]) / hari_lain

            print("\nKesimpulan:")
            if tidur_segar > tidur_lain:
                print("- Saat tubuh segar, tidurnya cenderung lebih lama.")
            else:
                print("- Durasi tidur belum terlihat berpengaruh pada rasa segar.")
            if air_segar > air_lain:
                print("- Saat tubuh segar, air yang diminum cenderung lebih banyak.")
            else:
                print("- Jumlah air minum belum terlihat berpengaruh pada rasa segar.")
        else:
            print("\nData belum cukup untuk membandingkan kondisi segar dengan yang lain.")


# =====================================================
#  BAGIAN 7 : PANTAU ANAK (KHUSUS ORANG TUA)
# =====================================================
def pilih_anak():
    # Menampilkan daftar anak milik orang tua yang login.
    # Anak yang dipilih disimpan di dict "sasaran" (sasaran["id"] tetap 0 kalau batal).
    sasaran["id"] = 0
    cur.execute(
        "SELECT id_pengguna, nama_pengguna, target_harian FROM pengguna "
        "WHERE id_ortu = %s ORDER BY id_pengguna",
        (akun["id"],)
    )
    daftar = cur.fetchall()

    if len(daftar) == 0:
        print("Kamu belum punya akun anak. Tambahkan lewat menu 'Tambah akun anak'.")
    else:
        print("--- DAFTAR ANAK ---")
        for i in range(len(daftar)):
            print(f"{i + 1}. {daftar[i][1]} | target {daftar[i][2]} ml")

        pilih = input("Pilih nomor anak (0 untuk batal): ")
        if pilih.isdigit() and 1 <= int(pilih) <= len(daftar):
            anak = daftar[int(pilih) - 1]
            sasaran["id"] = anak[0]
            sasaran["nama"] = anak[1]
        else:
            print("Tidak ada anak yang dipilih.")


def lihat_ringkasan_anak():
    pilih_anak()
    if sasaran["id"] != 0:
        print(f"\n=== RINGKASAN {sasaran['nama']} HARI INI ===")
        tampilkan_progress()
        riwayat_tidur()
        print()
        korelasi()


def atur_target_anak():
    pilih_anak()
    if sasaran["id"] != 0:
        atur_target()


def hapus_akun_anak():
    pilih_anak()
    if sasaran["id"] != 0:
        yakin = input(f"Yakin menghapus akun anak {sasaran['nama']}? Ketik ya untuk lanjut: ").lower()
        if yakin == "ya":
            hapus_pengguna()
            print("Akun anak berhasil dihapus.")
        else:
            print("Penghapusan dibatalkan.")


def menu_pantau_anak():
    while True:
        print("\n=== PANTAU ANAK ===")
        print("1. Tambah akun anak")
        print("2. Lihat ringkasan & korelasi anak")
        print("3. Atur target minum anak")
        print("4. Hapus akun anak")
        print("0. Kembali")
        pilihan = input("Pilih menu: ")

        match pilihan:
            case "1":
                buat_akun()
            case "2":
                lihat_ringkasan_anak()
            case "3":
                atur_target_anak()
            case "4":
                hapus_akun_anak()
            case "0":
                break
            case _:
                print("Pilihan tidak valid!")


# =====================================================
#  PROGRAM UTAMA
# =====================================================
if terhubung:
    siapkan_database()
    menu_awal()
    db.close()