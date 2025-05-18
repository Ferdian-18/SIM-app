import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import re
import io

# CSS: Ubah tampilan berdasarkan status login
if 'login' in st.session_state and st.session_state.login:
    # Kalau sudah login - warna halaman & sidebar
    st.markdown("""
        <style>
        .stApp {
            background-color: #B1CBA6;  /* Hijau */
        }
        section[data-testid="stSidebar"] {
            background-color: #E74C3C;  /* Sidebar tomato */
        }
        </style>
    """, unsafe_allow_html=True)
else:
    # Saat belum login (halaman login)
    st.markdown("""
        <style>
        .stApp {
            background-color: #B1CBA6;  /* Hijau */
        }
        </style>
    """, unsafe_allow_html=True)

# ---------- Login ---------- #
def cek_login(user, pw):
    return user == "admin" and pw == "admin123"

if 'login' not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.image("Background.png", width=800)
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if cek_login(username, password):
            st.session_state.login = True
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error("Username atau Password salah")

else:
    st.sidebar.title("TomaTown🍅")
    halaman = st.sidebar.radio("Pilih Halaman", ["Dashboard", "Penjualan", "Modal", "Laporan Laba/Rugi"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

# ---------- Inisialisasi Database ---------- #
    def init_db():
        conn = sqlite3.connect("TomaTown_DataBase.db")
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS stok (
                kode TEXT PRIMARY KEY,
                jenis TEXT,
                jumlah REAL,
                harga REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS modal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keterangan TEXT,
                kuantitas TEXT,
                harga REAL,
                jumlah REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS penjualan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu TEXT,
                kode TEXT,
                jumlah_terjual INTEGER,
                total_penjualan REAL
            )
        """)

        conn.commit()
        conn.close()

    init_db()

     # ---------- Fungsi Utility ---------- #
    def load_data(query, params=()):
        conn = sqlite3.connect("TomaTown_DataBase.db")
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def execute_query(query, params=()):
        conn = sqlite3.connect("TomaTown_DataBase.db")
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()

# ----------------- Dashboard ----------------- #
    if halaman == "Dashboard":
        st.title("Selamat Datang!")
        st.image("Logo TomaTown.png", width=500)
        st.header("📦 Sistem Persediaan Tomat")
        data_stok = load_data("SELECT * FROM stok")
        st.dataframe(data_stok)

        with st.form("form_tambah"):
            kode = st.text_input("Kode")
            jenis = st.text_input("Jenis")
            jumlah = st.number_input("Jumlah (Kg)", min_value=0.0)
            harga = st.number_input("Harga (per Kg)", min_value=0.0)
            tambah = st.form_submit_button("Tambah")

            if tambah:
                if kode and jenis:
                    existing = load_data("SELECT * FROM stok WHERE kode = ?", (kode,))
                    if not existing.empty:
                        st.error("Kode sudah ada!")
                    else:
                        execute_query("INSERT INTO stok VALUES (?, ?, ?, ?)", (kode, jenis, jumlah, harga))
                        st.success("Data berhasil ditambahkan!")
                        st.rerun()
                else:
                    st.warning("Kode dan Jenis wajib diisi.")

        with st.form("form_update"):
            kode_update = st.text_input("Kode Tomat")
            jumlah_tambah = st.number_input("Jumlah Tambahan", min_value=0.0)
            update = st.form_submit_button("Tambah Jumlah")
            if update:
                existing = load_data("SELECT * FROM stok WHERE kode = ?", (kode_update,))
                if not existing.empty:
                    execute_query("UPDATE stok SET jumlah = jumlah + ? WHERE kode = ?", (jumlah_tambah, kode_update))
                    st.success("Jumlah berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error("Kode tidak ditemukan.")
        
        with st.form("form_hapus"):
            kode_hapus = st.text_input("Kode Tomat")
            hapus = st.form_submit_button("Hapus")
            if hapus:
                execute_query("DELETE FROM stok WHERE kode = ?", (kode_hapus,))
                st.success("Data berhasil dihapus!")
                st.rerun()

# ----------------- Penjualan ----------------- #
    elif halaman == "Penjualan":
        st.header("🛒 Penjualan Tomat")
        penjualan = load_data("SELECT * FROM penjualan")
        penjualan = penjualan.rename(columns={
        "jumlah_terjual": "jumlah terjual",
        "total_penjualan": "total penjualan"
         })
        st.dataframe(penjualan, use_container_width=True)

        with st.form("form_jual"):
            kode_jual = st.text_input("Kode Tomat yang Dijual")
            jumlah_jual = st.number_input("Jumlah Terjual", min_value=0, step=1)
            jual = st.form_submit_button("Jual")

            if jual:
                stok = load_data("SELECT * FROM stok WHERE kode = ?", (kode_jual,))
                if not stok.empty:
                    available = stok.at[0, "jumlah"]
                    harga_satuan = stok.at[0, "harga"]
                    if jumlah_jual <= available:
                        total = jumlah_jual * harga_satuan
                        execute_query("UPDATE stok SET jumlah = jumlah - ? WHERE kode = ?", (jumlah_jual, kode_jual))
                        execute_query("INSERT INTO penjualan (waktu, kode, jumlah_terjual, total_penjualan) VALUES (?, ?, ?, ?)",
                                      (datetime.now().isoformat(), kode_jual, jumlah_jual, total))
                        st.success(f"Berhasil menjual {jumlah_jual} item. Total: Rp{total:,.0f}")
                        st.rerun()
                    else:
                        st.warning("Stok tidak mencukupi!")
                else:
                    st.error("Kode tidak ditemukan.")

        st.write("### Hapus Riwayat Penjualan")
        for i, row in penjualan.iterrows():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            col1.write(row["waktu"])
            col2.write(row["kode"])
            col3.write(f"{row['jumlah terjual']} Kg")
            col4.write(f"Rp{row['total penjualan']:,.0f}")
            if col5.button("🗑️", key=f"hapus_penjualan_{i}"):
                execute_query("DELETE FROM penjualan WHERE id = ?", (row["id"],))
                st.rerun()

# ----------------- Modal ----------------- #
    elif halaman == "Modal":
        st.header("💼 Manajemen Modal")
        with st.form("form_modal"):
            ket_modal = st.text_input("Keterangan Modal")
            kuantitas_modal = st.text_input("Kuantitas (misal: 2 kg)")
            harga_modal = st.number_input("Harga per unit (Rp)", min_value=0, step=1000)

            jumlah_modal = 0
            if kuantitas_modal:
                match = re.match(r"(\d+(?:\.\d+)?)", kuantitas_modal)
                if match:
                    jumlah_unit = float(match.group(1))
                    jumlah_modal = jumlah_unit * harga_modal
            st.write(f"**Jumlah (Rp):** Rp {jumlah_modal:,.0f}")

            tambah_modal = st.form_submit_button("Tambah Modal")
            if tambah_modal:
                if ket_modal and kuantitas_modal and harga_modal > 0:
                    execute_query("INSERT INTO modal (keterangan, kuantitas, harga, jumlah) VALUES (?, ?, ?, ?)",
                                  (ket_modal, kuantitas_modal, harga_modal, jumlah_modal))
                    st.success("Modal berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.warning("Isi semua data terlebih dahulu.")

        modal = load_data("SELECT * FROM modal")
        st.dataframe(modal)

        st.write("### Hapus Pencatatan Modal")
        for i, row in modal.iterrows():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            col1.write(row["keterangan"])
            col2.write(row["kuantitas"])
            col3.write(f"Rp{row['harga']:,.0f}")
            col4.write(f"Rp{row['jumlah']:,.0f}")
            if col5.button("🗑️", key=f"hapus_modal_{i}"):
                execute_query("DELETE FROM modal WHERE id = ?", (row["id"],))
                st.rerun()

# ----------------- Laporan Laba Rugi ----------------- #
    elif halaman == "Laporan Laba/Rugi":
        st.header("📊 Laporan Laba / Rugi")

        total_modal = load_data("SELECT SUM(jumlah) as total FROM modal").at[0, "total"] or 0
        total_penjualan = load_data("SELECT SUM(total_penjualan) as total FROM penjualan").at[0, "total"] or 0
        laba = total_penjualan - total_modal

        st.metric("Total Modal", f"Rp{total_modal:,.0f}")
        st.metric("Total Penjualan", f"Rp{total_penjualan:,.0f}")
        st.metric("Laba / Rugi", f"Rp{laba:,.0f}", delta=laba)

        st.subheader("⬇️ Ekspor Seluruh Data")
        data_stok = load_data("SELECT * FROM stok")
        modal = load_data("SELECT * FROM modal")
        penjualan = load_data("SELECT * FROM penjualan")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            data_stok.to_excel(writer, sheet_name="Data Stok", index=False)
            modal.to_excel(writer, sheet_name="Riwayat Modal", index=False)
            penjualan.to_excel(writer, sheet_name="Riwayat Penjualan", index=False)
            writer.close()
            excel_data = output.getvalue()

        st.download_button(
            label="📀 Download Semua Data sebagai Excel",
            data=excel_data,
            file_name="semua_data_tomat.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
