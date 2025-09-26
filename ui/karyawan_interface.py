# ui/karyawan_interface.py
import streamlit as st
import pandas as pd
from db.queries import load_checkups, get_employee_by_uid

def karyawan_interface(uid=None):
    """
    Landing page for karyawan to view their medical checkup.
    Accessed via a URL with ?uid=<unique_id> or via QR code session.
    """

    st.header("🏥 Medical Check-Up Result")

    # ---------------------------
    # 1️⃣ Get UID from session or query string
    # ---------------------------
    if not uid:
        try:
            uid = st.query_params.get("uid", [None])
            if isinstance(uid, list):
                uid = uid[0]
        except AttributeError:
            uid = st.experimental_get_query_params().get("uid", [None])[0]

    if not uid:
        st.error("❌ UID tidak ditemukan di URL. Silakan scan QR code yang benar.")
        return

    # ---------------------------
    # 2️⃣ Load employee and checkup data
    # ---------------------------
    try:
        emp_raw = get_employee_by_uid(uid)
        if emp_raw is None:
            st.warning("❌ Data karyawan tidak ditemukan.")
            return
        emp = emp_raw.to_dict() if hasattr(emp_raw, "to_dict") else emp_raw
    except Exception as e:
        st.error(f"❌ Gagal mengambil data karyawan: {e}")
        return

    try:
        df_checkups = load_checkups()
        if df_checkups.empty:
            st.warning("Belum ada data medical check-up di sistem.")
            return
        df_user = df_checkups[df_checkups["uid"].astype(str) == str(uid)]
        if df_user.empty:
            st.warning("❌ Data medical check-up tidak ditemukan untuk UID ini.")
            return
        df_user["tanggal_checkup"] = pd.to_datetime(df_user["tanggal_checkup"], errors="coerce").dt.date

        # ---------------------------
        # Patch: Round numeric columns
        # ---------------------------
        numeric_cols = ["tinggi", "berat", "lingkar_perut", "bmi",
                        "gula_darah_puasa", "gula_darah_sewaktu",
                        "cholesterol", "asam_urat"]
        df_user[numeric_cols] = df_user[numeric_cols].round(2)

    except Exception as e:
        st.error(f"❌ Gagal mengambil data checkup: {e}")
        return

    # ---------------------------
    # 3️⃣ Compute status (Unwell/Well)
    # ---------------------------
    def compute_status(row):
        if ((row.get("gula_darah_puasa", 0) > 120) or
            (row.get("gula_darah_sewaktu", 0) > 200) or
            (row.get("cholesterol", 0) > 240) or
            (row.get("asam_urat", 0) > 7) or
            (row.get("bmi", 0) >= 30)):
            return "Unwell"
        return "Well"

    df_user["status"] = df_user.apply(compute_status, axis=1)

    # ---------------------------
    # 4️⃣ Display profile info
    # ---------------------------
    st.subheader("👤 Profil Karyawan")
    st.markdown(f"**Nama:** {emp.get('nama','')}")
    st.markdown(f"**Tanggal Lahir:** {pd.to_datetime(emp.get('tanggal_lahir',''), errors='coerce').strftime('%Y-%m-%d') if emp.get('tanggal_lahir') else ''}")
    st.markdown(f"**Lokasi:** {emp.get('lokasi','')}")
    st.markdown(f"**Jabatan:** {emp.get('jabatan','')}")
    st.markdown(f"**Kontak Darurat:** {emp.get('kontak_darurat','-') or '-'}")

    # ---------------------------
    # 5️⃣ Display latest checkup
    # ---------------------------
    latest = df_user.sort_values("tanggal_checkup", ascending=False).iloc[0]
    st.subheader("📊 Hasil Terbaru")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("BMI", f"{latest['bmi']:.2f}")
        st.metric("Berat", f"{latest['berat']:.2f} kg")
        st.metric("Umur", f"{latest['umur']} tahun")  # added umur
    with col2:
        st.metric("Tinggi", f"{latest['tinggi']:.2f} cm")
        st.metric("Lingkar Perut", f"{latest['lingkar_perut']:.2f} cm")
    with col3:
        st.metric("Gula Darah Puasa", f"{latest['gula_darah_puasa']:.2f} mg/dL")
        st.metric("Gula Darah Sewaktu", f"{latest['gula_darah_sewaktu']:.2f} mg/dL")
        st.metric("Cholesterol", f"{latest['cholesterol']:.2f} mg/dL")
        st.metric("Asam Urat", f"{latest['asam_urat']:.2f} mg/dL")

    # ---------------------------
    # 6️⃣ Display full history
    # ---------------------------
    st.subheader("📜 Riwayat Pemeriksaan")
    df_history = df_user.sort_values("tanggal_checkup", ascending=False)

    def highlight_unwell(row):
        styles = []
        for col, v in row.items():
            if col == "gula_darah_puasa": styles.append("color: red" if v>120 else "")
            elif col == "gula_darah_sewaktu": styles.append("color: red" if v>200 else "")
            elif col == "cholesterol": styles.append("color: red" if v>240 else "")
            elif col == "asam_urat": styles.append("color: red" if v>7 else "")
            elif col == "bmi": styles.append("color: red" if v>=30 else "")
            elif col == "lingkar_perut": styles.append("color: red" if v>90 else "")
            else: styles.append("")
        return styles

    # ---------------------------
    # Round numeric columns for display like manager
    # ---------------------------
    st.dataframe(
        df_history[
            ["tanggal_checkup","lokasi","jabatan","umur","tinggi","berat","lingkar_perut","bmi",
             "gula_darah_puasa","gula_darah_sewaktu","cholesterol","asam_urat","status"]
        ].style
         .format({
             "tinggi": "{:.2f}",
             "berat": "{:.2f}",
             "bmi": "{:.2f}",
             "lingkar_perut": "{:.2f}",
             "gula_darah_puasa": "{:.2f}",
             "gula_darah_sewaktu": "{:.2f}",
             "cholesterol": "{:.2f}",
             "asam_urat": "{:.2f}",
         })
         .apply(highlight_unwell, axis=1),
        use_container_width=True
    )

    # ---------------------------
    # 7️⃣ Footer
    # ---------------------------
    st.markdown("---")
    st.info("ℹ️ Hubungi tenaga kesehatan jika ada pertanyaan mengenai hasil medical check-up Anda.")
