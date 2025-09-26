# ui/manager_interface.py
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from db.queries import (
    load_checkups, save_uploaded_checkups, get_users, add_user, get_employees, reset_karyawan_data,
)
from config.settings import CSV_FILENAME, EXCEL_FILENAME
from ui.qr_manager import display_qr_code, generate_qr_bytes
from db.excel_parser import parse_master_karyawan, parse_medical_checkup
from db.helpers import get_all_lokasi, validate_lokasi
from db.queries import (
    get_employee_by_uid,
    get_medical_checkups_by_uid,
    update_employee_data,
    insert_medical_checkup,
)
from db.queries import save_manual_karyawan_edits
from db.queries import get_latest_medical_checkup
from db.helpers import get_all_lokasi, validate_lokasi, sanitize_df_for_display

import io, zipfile, uuid
import altair as alt

# -------------------------
# Manager Interface
# -------------------------
def manager_interface(current_employee_uid=None):
    st.header("📊 Mini MCU - Manager Interface")
    df = load_checkups()
    users_df = get_users()
    employees_df = get_employees()

    tab1, tab2, tab3, tab4, tab5, tab6, = st.tabs([
        "Dashboard", "User Management", "QR Codes",
        "Upload & Export Data Karyawan", "Data Management", "Edit Data Karyawan",
        
    ])

    # ---------------- Tab 1: Dashboard ----------------
    with tab1:
        st.subheader("📊 Dashboard – Mini MCU")

        # Merge latest checkup with employees
        latest_checkup_df = get_latest_medical_checkup()
        if latest_checkup_df is None:
            latest_checkup_df = pd.DataFrame()

        df_combined = employees_df.copy()
        if not latest_checkup_df.empty:
            df_combined = df_combined.merge(
                latest_checkup_df, on='uid', how='left', suffixes=('', '_checkup')
            )

        # After loading df in manager_interface.py

        # Replace 'tanggal' with 'tanggal_checkup'
        if "tanggal_checkup" in df.columns:
            df["tanggal_checkup"] = pd.to_datetime(df["tanggal_checkup"], errors="coerce").dt.date

            if "tahun" not in df.columns:
                df["tahun"] = pd.to_datetime(df["tanggal_checkup"], errors="coerce").dt.year
            if "bulan" not in df.columns:
                df["bulan"] = pd.to_datetime(df["tanggal_checkup"], errors="coerce").dt.month
        else:
            st.error("❌ Kolom 'tanggal_checkup' tidak ada di DataFrame!")
            st.stop()

        df_combined = employees_df.copy()
        df_combined = df_combined.merge(
            latest_checkup_df, on='uid', how='left', suffixes=('', '_checkup')
        )

        # Fill missing medical columns with NaN
        medical_cols = ['tanggal_checkup','tinggi','berat','bmi','lingkar_perut',
                'gula_darah_puasa','gula_darah_sewaktu','cholesterol','asam_urat']
        for col in medical_cols:
            if col not in df_combined.columns:
                df_combined[col] = None

        # Convert tanggal_checkup to datetime and remove time
        if 'tanggal_checkup' in df_combined.columns:
            df_combined['tanggal_checkup'] = pd.to_datetime(df_combined['tanggal_checkup'], errors='coerce').dt.date


        # Convert tanggal to datetime and remove time
        if 'tanggal' in df_combined.columns:
            df_combined['tanggal'] = pd.to_datetime(df_combined['tanggal'], errors='coerce').dt.date

        # Calculate status: Unwell if any threshold exceeded or obese
        df_combined['status'] = 'Well'
        df_combined.loc[
            (df_combined['gula_darah_puasa'] > 120) |
            (df_combined['gula_darah_sewaktu'] > 200) |
            (df_combined['cholesterol'] > 240) |
            (df_combined['asam_urat'] > 7) |
            (df_combined['bmi'] >= 30),
            'status'
        ] = 'Unwell'

        # ---------------- Subtabs ----------------
        subtab1, subtab2 = st.tabs(["Riwayat Checkup Karyawan", "Graph Placeholder"])

        #-------------subtab1: Table with Filters ----------------
        with subtab1:
            st.markdown("### Filters")

            from db.helpers import get_dashboard_checkup_data, get_all_lokasi

            # --- Fetch combined employee + latest checkup data ---
            df_combined = get_dashboard_checkup_data()
            employees_df = df_combined  # For lokasi options

            # --- Prepare month/year for filters ---
            month_names = ["All","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug",
                        "Sep","Oct","Nov","Dec"]

            try:
                lokasi_options = sorted(set(get_all_lokasi()) | set(employees_df['lokasi'].dropna().tolist()))
            except Exception:
                lokasi_options = sorted(set(employees_df['lokasi'].dropna().tolist()))

            status_options = ["Well","Unwell"]

            # --- Filter widgets ---
            col1, col2, col3, col4 = st.columns([1,1,2,1])
            with col1:
                filter_bulan = st.selectbox(
                    "Filter Bulan",
                    options=range(0,13),
                    index=0,
                    format_func=lambda x: month_names[x],
                    key="subtab1_filter_bulan"
                )
            with col2:
                years = sorted([int(y) for y in df_combined['tahun'].dropna().unique()])
                filter_tahun = st.selectbox(
                    "Filter Tahun",
                    options=[0] + years,
                    index=0,
                    format_func=lambda x: "All" if x == 0 else str(x),
                    key="subtab1_filter_tahun"
                )
            with col3:
                filter_lokasi = st.multiselect(
                    "Filter Lokasi",
                    options=lokasi_options,
                    default=lokasi_options,
                    key="subtab1_filter_lokasi"
                )
            with col4:
                filter_status = st.multiselect(
                    "Filter Status",
                    options=status_options,
                    default=status_options,
                    key="subtab1_filter_status"
                )

            # --- Apply filters ---
            df_filtered = df_combined.copy()
            if filter_tahun != 0:
                df_filtered = df_filtered[(df_filtered['tahun'] == filter_tahun) | (df_filtered['tahun'].isna())]
            if filter_bulan != 0:
                df_filtered = df_filtered[(df_filtered['bulan'] == filter_bulan) | (df_filtered['bulan'].isna())]
            if filter_lokasi:
                df_filtered = df_filtered[df_filtered['lokasi'].isin(filter_lokasi)]
            if filter_status:
                df_filtered = df_filtered[df_filtered['status'].isin(filter_status) | df_filtered['status'].isna()]

            # --- Add Well / Unwell counter ---
            if not df_filtered.empty and "status" in df_filtered.columns:
                total_well = df_filtered[df_filtered['status'] == "Well"].shape[0]
                total_unwell = df_filtered[df_filtered['status'] == "Unwell"].shape[0]
                st.markdown(f"**Total Well:** {total_well}  |  **Total Unwell:** {total_unwell}")

            # --- Normalize tanggal_lahir for display ---
            if "tanggal_lahir" in df_filtered.columns:
                df_filtered["tanggal_lahir"] = pd.to_datetime(
                    df_filtered["tanggal_lahir"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")

            # --- Display table ---
            display_cols = [
                'uid','checkup_id','tanggal_checkup','nama','jabatan',
                'tanggal_lahir','umur','lokasi','status',
                'tinggi','berat','bmi','lingkar_perut',
                'gula_darah_puasa','gula_darah_sewaktu','cholesterol','asam_urat'
            ]

            missing_cols = [col for col in display_cols if col not in df_filtered.columns]
            if missing_cols:
                st.error(f"❌ Kolom tidak ditemukan di DataFrame: {missing_cols}")
            else:
                df_display = df_filtered[display_cols].copy()

                # --- Unwell highlighting ---
                def highlight_unwell(row):
                    styles = []
                    for col, v in row.items():
                        if col == "gula_darah_puasa":
                            styles.append("color: red" if v > 125 else "")
                        elif col == "gula_darah_sewaktu":
                            styles.append("color: red" if v > 199 else "")
                        elif col == "cholesterol":
                            styles.append("color: red" if v > 240 else "")
                        elif col == "asam_urat":
                            styles.append("color: red" if v > 7 else "")
                        elif col == "bmi":
                            styles.append("color: red" if (v < 18.5 or v > 25) else "")
                        elif col == "lingkar_perut":
                            styles.append("color: red" if v > 90 else "")
                        else:
                            styles.append("")
                    return styles

                st.dataframe(
                    df_display.style
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

            # ================= Delete Checkup Data =================
            st.markdown("### 🗑️ Hapus Data Checkup")

            if not df_filtered.empty and "checkup_id" in df_filtered.columns:
                selected_checkup = st.selectbox(
                    "Pilih Checkup ID untuk dihapus",
                    options=df_filtered["checkup_id"].unique(),
                    key="subtab1_delete_checkup"
                )

                if st.button("Hapus Data Checkup", key="btn_delete_checkup"):
                    from db import queries
                    try:
                        queries.delete_checkup(selected_checkup)
                        st.success(f"Data checkup dengan ID {selected_checkup} berhasil dihapus.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

                # 🆕 Delete ALL data option
                if st.button("Hapus Semua Data Checkup", key="btn_delete_all_checkups"):
                    from db import queries
                    try:
                        queries.delete_all_checkups()
                        st.success("✅ Semua data checkup berhasil dihapus.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus semua data: {e}")
            else:
                st.info("Tidak ada data checkup yang bisa dihapus.")


        # ---------------- Subtab 2: Graph Placeholder ----------------
        with subtab2:
            st.markdown("### Filters")
            # --- Filters for Subtab2 ---
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                filter_bulan2 = st.selectbox(
                    "Filter Bulan",
                    options=range(0,13),
                    index=0,
                    format_func=lambda x: month_names[x],
                    key="subtab2_filter_bulan"
                )
            with col2:
                filter_tahun2 = st.selectbox(
                    "Filter Tahun",
                    options=[0] + sorted(df["tahun"].unique()),
                    index=0,
                    format_func=lambda x: "All" if x == 0 else str(x),
                    key="subtab2_filter_tahun"
                )
            with col3:
                filter_status2 = st.multiselect(
                    "Filter Status",
                    options=status_options,
                    default=status_options,
                    key="subtab2_filter_status"
                )

            # --- Placeholder ---
            st.info("📊 Graph placeholder – to be implemented later")
       
    # ---------------- Tab 2: User Management ----------------
    with tab2:
        st.subheader("👥 User Management")
        manager_count = len(users_df[users_df["role"] == "Manager"])
        nurse_count = len(users_df[users_df["role"] == "Tenaga Kesehatan"])
        karyawan_count = len(users_df[users_df["role"] == "Karyawan"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Manager Users", manager_count)
        col2.metric("Nurse Users", nurse_count)
        col3.metric("Karyawan Users", karyawan_count)

        st.markdown("---")
        st.write("Tambah user baru:")

        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["Manager", "Tenaga Kesehatan", "Karyawan"])
            add_user_btn = st.form_submit_button("Add User")

            if add_user_btn:
                if new_username and new_password:
                    try:
                        add_user(new_username, new_password, new_role)
                        st.success(f"✅ User '{new_username}' ditambahkan sebagai '{new_role}'!")
                        users_df = get_users()
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.error("⚠️ Username sudah ada!")
                        else:
                            st.error(f"❌ Error: {e}")
                else:
                    st.error("❌ Username dan password tidak boleh kosong!")

        st.dataframe(users_df[['username','role']], use_container_width=True)

    # ---------------- Tab 3: QR Code Management ----------------
    with tab3:
        from ui.qr_manager import qr_manager_interface
        qr_manager_interface()

    # ---------------- Tab 4: Upload & Export Data ----------------
    with tab4:
        st.subheader("📁 Upload & Export Data")

        subtab1, subtab2, subtab3 = st.tabs([
            "Download Template Check-Up",
            "Upload Master Karyawan",
            "Upload Medical Checkup"
        ])

        # ---------------- Subtab 1: Download Template ----------------
        with subtab1:
            st.markdown("### 📥 Download Template / Data Check-Up")
            from utils.export_utils import generate_karyawan_template_excel, export_checkup_data_excel
            from db.helpers import get_dashboard_checkup_data

            # --- Lokasi filter for template ---
            try:
                employees_df = get_employees()
                lokasi_options = sorted(set(employees_df['lokasi'].dropna().tolist()))
            except Exception:
                lokasi_options = []

            filter_lokasi_template = st.multiselect(
                "Filter berdasarkan Lokasi untuk Template (opsional)",
                options=lokasi_options,
                default=lokasi_options,
                key="filter_lokasi_template_subtab1"
            )

            # --- Download Template Excel ---
            template_file = generate_karyawan_template_excel(lokasi_filter=filter_lokasi_template)
            st.download_button(
                "Download Karyawan Template Excel",
                data=template_file,
                file_name="Template_Data_CheckUp.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("---")  # separator

            # --- Lokasi filter for actual data export ---
            filter_lokasi_export = st.multiselect(
                "Filter Lokasi untuk Export Data Checkup (opsional)",
                options=lokasi_options,
                default=lokasi_options,
                key="filter_lokasi_export_subtab1"
            )

            # --- Optional date filter for exporting actual checkup data ---
            selected_date = st.date_input(
                "Filter Export Berdasarkan Tanggal Checkup (opsional)",
                value=None,
                key="export_checkup_date_picker_subtab"
            )

            # --- Fetch combined checkup data ---
            try:
                df_checkup = get_dashboard_checkup_data()
            except Exception as e:
                st.error(f"❌ Gagal ambil data checkup: {e}")
                df_checkup = pd.DataFrame()

            if not df_checkup.empty:
                df_export = df_checkup.copy()

                # Apply lokasi filter
                if filter_lokasi_export:
                    df_export = df_export[df_export['lokasi'].isin(filter_lokasi_export)]

                # --- Export by selected date ---
                df_by_date = df_export.copy()
                if selected_date:
                    df_by_date = df_by_date[df_by_date['tanggal_checkup'] == pd.to_datetime(selected_date).date()]

                if not df_by_date.empty:
                    file_bytes_date = export_checkup_data_excel(df_by_date)
                    st.download_button(
                        "Download Data Checkup by Date",
                        data=file_bytes_date,
                        file_name=f"Checkup_{selected_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.info("Tidak ada data checkup untuk tanggal yang dipilih dengan filter lokasi saat ini.")

                # --- Export all filtered data ---
                if not df_export.empty:
                    file_bytes_all = export_checkup_data_excel(df_export)
                    st.download_button(
                        "Download Semua Data Checkup (Filtered)",
                        data=file_bytes_all,
                        file_name="All_Checkup_Data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.info("Tidak ada data checkup untuk filter lokasi saat ini.")
            else:
                st.info("Belum ada data checkup yang tersedia untuk di-export.")



        # ---------------- Subtab 2: Upload Master Karyawan ----------------
        with subtab2:
            st.markdown("### 📁 Upload Master Data Karyawan")
            import os
            from config.settings import UPLOAD_DIR
            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)

            uploaded_karyawan_file = st.file_uploader(
                "Upload file data Karyawan (Master Data)", 
                type=["xls", "xlsx", "csv"], key="karyawan_upload_subtab"
            )

            if uploaded_karyawan_file:
                save_path = os.path.join(UPLOAD_DIR, uploaded_karyawan_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_karyawan_file.getbuffer())

                try:
                    from db.excel_parser import parse_master_karyawan
                    with st.spinner("Mengupload data karyawan..."):
                        result = parse_master_karyawan(save_path)
                    st.success(
                        f"✅ File '{uploaded_karyawan_file.name}' berhasil diproses. "
                        f"Inserted: {result['inserted']}, Skipped: {result['skipped']}"
                    )
                except Exception as e:
                    st.error(f"❌ Error saat meng-upload file karyawan: {e}")

        # ---------------- Subtab 3: Upload Medical Checkup ----------------
        with subtab3:
            st.markdown("### 📁 Upload Data Medical Check-Up")

            uploaded_medical_file = st.file_uploader(
                "Upload file Data Medical Checkup", 
                type=["xls", "xlsx"], key="medical_upload_subtab"
            )

            if uploaded_medical_file:
                try:
                    from db.checkup_uploader import parse_checkup_xls
                    with st.spinner("Mengupload data medical checkup..."):
                        result = parse_checkup_xls(uploaded_medical_file)

                        st.success(
                            f"✅ File '{uploaded_medical_file.name}' berhasil diproses. "
                            f"Inserted: {result['inserted']}"
                        )
                        if result['skipped']:
                            st.warning(f"⚠️ Beberapa baris di-skip ({len(result['skipped'])}):")
                            st.dataframe(pd.DataFrame(result['skipped']), use_container_width=True)

                except Exception as e:
                    st.error(f"❌ Error saat meng-upload file medical checkup: {e}")


    # ---------------- Tab 5: Data Management ----------------
    with tab5:
        st.subheader("🗂️ Data Management")

        # --- Permanent Subtabs ---
        tab_data_uid, tab_file_mgmt, tab_lokasi_mgmt = st.tabs([
            "Data UID Karyawan",
            "Hapus dan Tambah Data",
            "Lokasi Management"
        ])

        # ----------------------
        # Subtab: Data UID Karyawan
        # ----------------------
        with tab_data_uid:
            st.subheader("🗂️ Data UID Karyawan – Daftar Semua Karyawan")

            # ================= Add Master Data Karyawan =================
            st.markdown("### ➕ Tambah Master Data Karyawan")

            from db.helpers import get_all_lokasi
            from config.settings import INITIAL_LOKASI

            # --- Fetch current lokasi from DB or fallback to seeds ---
            try:
                lokasi_options = sorted(get_all_lokasi())
            except Exception:
                lokasi_options = sorted(INITIAL_LOKASI)

            with st.form("add_karyawan_form"):
                nama = st.text_input("Nama Karyawan", placeholder="Masukkan nama", key="add_nama")
                jabatan = st.text_input("Jabatan", placeholder="Masukkan jabatan", key="add_jabatan")
                lokasi = st.selectbox("Lokasi Kerja", options=lokasi_options, key="add_lokasi")
                
                submit = st.form_submit_button("Tambahkan Karyawan")

            if submit:
                if not nama or not jabatan:
                    st.warning("⚠️ Nama dan Jabatan wajib diisi!")
                else:
                    # Generate UID based on nama + jabatan
                    uid = f"{nama}_{jabatan}".replace(" ", "_").lower()
                    try:
                        from db.queries import insert_master_karyawan
                        insert_master_karyawan(uid=uid, nama=nama, jabatan=jabatan, lokasi=lokasi)
                        st.success(f"✅ Karyawan {nama} berhasil ditambahkan dengan UID: {uid}")
                        st.experimental_rerun()  # Refresh the table
                    except Exception as e:
                        st.error(f"❌ Gagal menambahkan karyawan: {e}")

            # --- Action buttons ---
            col1, col2 = st.columns([1,1])
            with col1:
                if st.button("🔄 Reload Data"):
                    st.rerun()
            with col2:
                if st.button("🗑️ Hapus Semua Data Karyawan", type="primary"):
                    from db.queries import reset_karyawan_data
                    reset_karyawan_data()
                    st.success("✅ Semua data karyawan berhasil dihapus.")
                    st.rerun()

            # --- Load data ---
            employees_df = get_employees()

            if employees_df.empty:
                st.info("Belum ada data Karyawan. Silakan upload XLS terlebih dahulu.")
            else:
                # --- Lokasi filter with "All" option ---
                lokasi_options = sorted(set(employees_df['lokasi'].dropna().tolist()))
                lokasi_options = ["All"] + lokasi_options
                filter_lokasi = st.multiselect(
                    "Filter berdasarkan Lokasi",
                    options=lokasi_options,
                    default=["All"]
                )

                df_display = employees_df.copy()
                if filter_lokasi and "All" not in filter_lokasi:
                    df_display = df_display[df_display['lokasi'].isin(filter_lokasi)]

                # --- Name search ---
                search_name = st.text_input("Cari Karyawan berdasarkan Nama")
                if search_name:
                    df_display = df_display[df_display["nama"].str.contains(search_name, case=False, na=False)]

                # --- Columns to display ---
                display_cols = [c for c in ["uid", "nama", "jabatan", "lokasi"] if c in df_display.columns]
                df_display = df_display[display_cols]

                # --- Display only, no editing ---
                df_display_safe = sanitize_df_for_display(df_display)
                st.dataframe(df_display_safe, use_container_width=True)

                # ----------------------
                # Subtab: Hapus dan Tambah Data
                # ----------------------
                with tab_file_mgmt:
                    st.subheader("🗄️ Hapus dan Tambah Data – File Uploads")

                    import os
                    from config.settings import UPLOAD_DIR
                    if not os.path.exists(UPLOAD_DIR):
                        os.makedirs(UPLOAD_DIR)

                    uploaded_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(('.xls', '.xlsx', '.csv'))]
                    if not uploaded_files:
                        st.info("Belum ada file yang di-upload.")
                    else:
                        if "selected_file_index" not in st.session_state:
                            st.session_state["selected_file_index"] = 0

                        selected_file = st.selectbox(
                            "Pilih file untuk lihat / hapus:",
                            uploaded_files,
                            index=min(st.session_state["selected_file_index"], len(uploaded_files)-1),
                            key="file_selectbox"
                        )
                        st.session_state["selected_file_index"] = uploaded_files.index(selected_file)

                        col1, col2 = st.columns([1,1])
                        with col1:
                            if st.button("📄 Lihat file"):
                                file_path = os.path.join(UPLOAD_DIR, selected_file)
                                try:
                                    if selected_file.endswith(('.xls', '.xlsx')):
                                        df_file = pd.read_excel(file_path)
                                    else:
                                        df_file = pd.read_csv(file_path)
                                    st.dataframe(df_file.head(50))
                                except Exception as e:
                                    st.error(f"❌ Gagal membaca file: {e}")

                        with col2:
                            if st.button("🗑️ Hapus file"):
                                file_path = os.path.join(UPLOAD_DIR, selected_file)
                                try:
                                    os.remove(file_path)
                                    st.success(f"✅ File '{selected_file}' berhasil dihapus.")
                                    st.session_state["selected_file_index"] = 0
                                except Exception as e:
                                    st.error(f"❌ Gagal menghapus file: {e}")

                        if st.button("🗑️ Hapus semua file"):
                            try:
                                for f in uploaded_files:
                                    os.remove(os.path.join(UPLOAD_DIR, f))
                                st.success("✅ Semua file berhasil dihapus.")
                                st.session_state["selected_file_index"] = 0
                            except Exception as e:
                                st.error(f"❌ Gagal menghapus semua file: {e}")

        # ----------------------
        # Subtab: Lokasi Management
        # ----------------------
        with tab_lokasi_mgmt:
            st.subheader("📍 Manage Lokasi")

            from db.helpers import get_all_lokasi
            from db.database import get_engine
            from sqlalchemy import text

            engine = get_engine()

            # --- Load daftar lokasi ---
            if "lokasi_list" not in st.session_state:
                try:
                    result = get_all_lokasi() or []
                    # normalize output (handles tuple, dict, or str)
                    st.session_state["lokasi_list"] = [
                        row[0] if isinstance(row, (tuple, list)) else row.get("name") if isinstance(row, dict) else row
                        for row in result
                    ]
                except Exception as e:
                    st.error(f"⚠️ Gagal load lokasi: {e}")
                    st.session_state["lokasi_list"] = []


            # --- Daftar Lokasi Saat Ini (top) ---
            daftar_placeholder = st.container()
            def refresh_daftar():
                daftar_placeholder.empty()  # Clear previous table before rendering
                if st.session_state["lokasi_list"]:
                    daftar_placeholder.table(pd.DataFrame(st.session_state["lokasi_list"], columns=["Lokasi"]))
                else:
                    daftar_placeholder.info("Belum ada lokasi yang tersedia.")
        
            refresh_daftar()

            st.markdown("---")
            st.write("Tambah Lokasi Baru:")

            # --- Add new lokasi ---
            with st.form("add_lokasi_form"):
                new_lokasi = st.text_input("Nama Lokasi")
                add_lokasi_btn = st.form_submit_button("Tambah Lokasi")

                if add_lokasi_btn:
                    if new_lokasi.strip():
                        try:
                            with engine.connect() as conn:
                                exists = conn.execute(
                                    text("SELECT 1 FROM lokasi WHERE name = :name"),
                                    {"name": new_lokasi.strip()}
                                ).scalar()

                            if exists:
                                st.warning(f"⚠️ Lokasi '{new_lokasi}' sudah ada di database!")
                            else:
                                with engine.begin() as conn:
                                    conn.execute(
                                        text("INSERT INTO lokasi (name) VALUES (:name)"),
                                        {"name": new_lokasi.strip()}
                                    )
                                st.success(f"✅ Lokasi '{new_lokasi}' berhasil ditambahkan!")

                                # Update list instantly
                                st.session_state["lokasi_list"].append(new_lokasi.strip())
                                refresh_daftar()
                        except Exception as e:
                            st.error(f"❌ Gagal menambahkan lokasi: {e}")
                    else:
                        st.error("❌ Nama Lokasi tidak boleh kosong!")

            st.markdown("---")
            st.write("Hapus Lokasi:")

            if st.session_state["lokasi_list"]:
                # --- Delete Lokasi ---
                selected_lokasi_delete = st.selectbox(
                    "Pilih Lokasi untuk dihapus",
                    options=st.session_state["lokasi_list"],
                    key="selected_lokasi_delete"
                )

                if st.button("🗑️ Hapus Lokasi"):
                    try:
                        with engine.begin() as conn:
                            linked = conn.execute(
                                text("SELECT COUNT(*) FROM karyawan WHERE lokasi = :lokasi"),
                                {"lokasi": selected_lokasi_delete}
                            ).scalar()

                            if linked > 0:
                                st.error(f"⚠️ Tidak bisa menghapus '{selected_lokasi_delete}', masih digunakan oleh {linked} karyawan!")
                            else:
                                conn.execute(
                                    text("DELETE FROM lokasi WHERE name = :name"),
                                    {"name": selected_lokasi_delete}
                                )
                                st.success(f"✅ Lokasi '{selected_lokasi_delete}' berhasil dihapus!")

                                # Update list instantly
                                st.session_state["lokasi_list"].remove(selected_lokasi_delete)
                                refresh_daftar()
                    except Exception as e:
                        st.error(f"❌ Gagal menghapus lokasi: {e}")

    # ----------------------
    # Tab 6: Update Karyawan Data
    # ----------------------
    with tab6:
        st.subheader("👥 Update Karyawan Data (Manager View)")

        # --- Load employees ---
        try:
            employees = get_employees()
        except Exception as e:
            st.error(f"❌ Gagal memuat daftar karyawan: {e}")
            employees = pd.DataFrame()

        # --- Build UID & Names ---
        def build_uid_name_lists(employees_obj):
            uids, names = [], []
            if isinstance(employees_obj, pd.DataFrame):
                uid_col = next((c for c in ["uid", "employee_uid", "id", "nik"] if c in employees_obj.columns), None)
                name_col = next((c for c in ["nama", "name"] if c in employees_obj.columns), None)
                if uid_col and name_col:
                    uids = employees_obj[uid_col].astype(str).tolist()
                    names = employees_obj[name_col].astype(str).tolist()
            elif isinstance(employees_obj, (list, tuple)):
                for e in employees_obj:
                    if isinstance(e, dict):
                        uid = e.get("employee_uid") or e.get("uid") or e.get("id") or e.get("nik")
                        name = e.get("nama") or e.get("name")
                        if uid and name:
                            uids.append(str(uid))
                            names.append(str(name))
            return uids, names

        uids, names = build_uid_name_lists(employees)
        display_options = ["-- Pilih Karyawan --"] + names

        # --- Selection columns ---
        col_sel, col_conf, col_res = st.columns([4, 1, 1])
        selected_name = col_sel.selectbox(
            "Pilih Karyawan",
            display_options,
            index=0,
            key=f"mgr_tab1_selector_{st.session_state.get('mgr_tab1_form_counter', 0)}"
        )
        confirm = col_conf.button("Konfirmasi Pilihan", use_container_width=True)
        reset = col_res.button("Reset Pilihan", use_container_width=True)

        # --- Confirm / Reset actions ---
        if confirm:
            if selected_name == "-- Pilih Karyawan --" or selected_name == "":
                st.warning("⚠️ Pilih karyawan terlebih dahulu sebelum konfirmasi!")
            else:
                try:
                    idx = names.index(selected_name)
                    selected_uid = uids[idx]
                    st.session_state["mgr_selected_emp_uid"] = selected_uid
                    st.session_state["mgr_emp_locked"] = True
                    emp_raw = get_employee_by_uid(selected_uid)
                    emp = emp_raw.to_dict() if hasattr(emp_raw, "to_dict") else emp_raw
                    st.session_state["mgr_selected_employee_record"] = emp
                    st.success(f"✅ Karyawan dikunci: {selected_name}")
                except Exception as e:
                    st.error(f"❌ Gagal ambil data karyawan: {e}")

        if reset:
            st.session_state["mgr_selected_emp_uid"] = None
            st.session_state["mgr_emp_locked"] = False
            if "mgr_selected_employee_record" in st.session_state:
                del st.session_state["mgr_selected_employee_record"]
            st.session_state["mgr_tab1_form_counter"] = st.session_state.get("mgr_tab1_form_counter", 0) + 1
            st.info("🔄 Pilihan karyawan dan form direset.")
            st.rerun()

        emp = st.session_state.get("mgr_selected_employee_record", None)
        selected_uid = st.session_state.get("mgr_selected_emp_uid", None)

        # --- Permanent subtabs ---
        tab_profil, tab_edit = st.tabs(["Profil Karyawan", "Edit Data Karyawan"])

        # ----------------------
        # Tab: Profil Karyawan
        # ----------------------
        with tab_profil:
            if emp:
                st.markdown(f"**Nama:** {emp.get('nama', '')}")
                st.markdown(f"**Tanggal Lahir:** {pd.to_datetime(emp.get('tanggal_lahir', ''), errors='coerce').strftime('%Y-%m-%d') if emp.get('tanggal_lahir') else ''}")
                st.markdown(f"**Lokasi:** {emp.get('lokasi', '')}")
                st.markdown(f"**Jabatan:** {emp.get('jabatan', '')}")

                # --- Kontak Darurat ---
                current_contact = emp.get("kontak_darurat", "-") or "-"
                new_contact = st.text_input("Kontak Darurat", value=current_contact, key="kontak_darurat_input")
                if st.button("💾 Save Kontak Darurat", key="save_kontak_darurat"):
                    emp["kontak_darurat"] = new_contact
                    df = pd.DataFrame([emp])
                    save_manual_karyawan_edits(df)
                    st.success("Emergency contact updated!")

                # --- Fetch all checkups for this employee ---
                from db.helpers import get_medical_checkups_by_uid

                all_checkups = get_medical_checkups_by_uid(emp["uid"])

                if not all_checkups.empty:
                    # Ensure tanggal_checkup is datetime
                    all_checkups["tanggal_checkup"] = pd.to_datetime(all_checkups["tanggal_checkup"], errors="coerce")

                    # --- Filters (optional) ---
                    month_names = ["All","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                    df_filtered = all_checkups.copy()

                    # --- Latest checkup ---
                    latest_df = df_filtered.sort_values("tanggal_checkup", ascending=False).head(1)
                    st.markdown("### 📌 Pemeriksaan Terakhir")

                    def highlight_unwell(row):
                        styles = []
                        for col, v in row.items():
                            if col == "gula_darah_puasa":
                                styles.append("color: red" if v > 125 else "")
                            elif col == "gula_darah_sewaktu":
                                styles.append("color: red" if v > 199 else "")
                            elif col == "cholesterol":
                                styles.append("color: red" if v > 240 else "")
                            elif col == "asam_urat":
                                styles.append("color: red" if v > 7 else "")
                            elif col == "bmi":
                                styles.append("color: red" if (v < 18.5 or v > 25) else "")
                            elif col == "lingkar_perut":
                                styles.append("color: red" if v > 90 else "")
                            else:
                                styles.append("")
                        return styles

                    st.dataframe(
                        latest_df.style
                            .format({
                                "tinggi": "{:.2f}", "berat": "{:.2f}", "bmi": "{:.2f}", "lingkar_perut": "{:.2f}",
                                "gula_darah_puasa": "{:.2f}", "gula_darah_sewaktu": "{:.2f}",
                                "cholesterol": "{:.2f}", "asam_urat": "{:.2f}",
                            })
                            .apply(highlight_unwell, axis=1),
                        use_container_width=True
                    )

                    # --- All history ---
                    st.markdown("### 📜 Riwayat Pemeriksaan")
                    history_df = df_filtered.sort_values("tanggal_checkup", ascending=False)
                    st.dataframe(
                        history_df.style
                            .format({
                                "tinggi": "{:.2f}", "berat": "{:.2f}", "bmi": "{:.2f}", "lingkar_perut": "{:.2f}",
                                "gula_darah_puasa": "{:.2f}", "gula_darah_sewaktu": "{:.2f}",
                                "cholesterol": "{:.2f}", "asam_urat": "{:.2f}",
                            })
                            .apply(highlight_unwell, axis=1),
                        use_container_width=True
                    )
                else:
                    st.info("Belum ada data pemeriksaan medis.")
            else:
                st.info("Pilih karyawan terlebih dahulu untuk melihat profil.")

        # ----------------------
        # Tab: Edit Data Karyawan
        # ----------------------
        with tab_edit:
            if emp:
                # --- Checkup date ---
                tanggal_check = st.date_input("Tanggal Pemeriksaan", datetime.today().date())

                col1, col2 = st.columns(2)
                # Other medical inputs
                tinggi = col1.number_input("Tinggi (cm)", value=float(emp.get("tinggi", 0)))
                berat = col2.number_input("Berat (kg)", value=float(emp.get("berat", 0)))
                bmi = round(berat / ((tinggi / 100) ** 2), 2) if tinggi > 0 else 0
                st.text_input("BMI", value=str(bmi), disabled=True)
                lingkar_perut = st.number_input("Lingkar Perut (cm)", value=float(emp.get("lingkar_perut", 0)))
                gula_darah_puasa = st.number_input("Gula Darah Puasa", value=float(emp.get("gula_darah_puasa", 0)))
                gula_darah_sewaktu = st.number_input("Gula Darah Sewaktu", value=float(emp.get("gula_darah_sewaktu", 0)))
                cholesterol = st.number_input("Cholesterol", value=float(emp.get("cholesterol", 0)))
                asam_urat = st.number_input("Asam Urat", value=float(emp.get("asam_urat", 0)))

                # Submit button
                if st.button("Simpan Pemeriksaan"):
                    df = pd.DataFrame([{
                        "uid": selected_uid,
                        "tanggal_checkup": tanggal_check,  # patched here
                        "tinggi": tinggi,
                        "berat": berat,
                        "bmi": bmi,
                        "lingkar_perut": lingkar_perut,
                        "gula_darah_puasa": gula_darah_puasa,
                        "gula_darah_sewaktu": gula_darah_sewaktu,
                        "cholesterol": cholesterol,
                        "asam_urat": asam_urat
                    }])
                    from db.queries import insert_medical_checkup
                    insert_medical_checkup(df)
                    st.success("✅ Pemeriksaan medis berhasil disimpan.")

            else:
                st.info("Pilih karyawan terlebih dahulu untuk menambahkan pemeriksaan.")