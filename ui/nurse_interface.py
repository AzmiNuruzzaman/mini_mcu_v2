# ui/nurse_interface.py
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import uuid

from db.excel_parser import parse_medical_checkup
from db.queries import (
    get_employees,
    get_employee_by_uid,
    insert_medical_checkup,
    save_uploaded_checkups,
    CHECKUP_COLUMNS,
    save_manual_karyawan_edits
)
from db.helpers import get_all_lokasi, get_medical_checkups_by_uid
from utils.export_utils import export_checkup_data_excel

def nurse_interface():
    st.header("📝 Mini MCU - Nurse Interface")

    # --- Session state ---
    if "nurse_tab_form_counter" not in st.session_state:
        st.session_state["nurse_tab_form_counter"] = 0
    if "nurse_selected_emp_uid" not in st.session_state:
        st.session_state["nurse_selected_emp_uid"] = None
    if "nurse_emp_locked" not in st.session_state:
        st.session_state["nurse_emp_locked"] = False

    # --- Load dynamic lokasi ---
    try:
        if "lokasi_list" not in st.session_state:
            st.session_state["lokasi_list"] = get_all_lokasi()
    except Exception:
        st.session_state["lokasi_list"] = []

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Data Karyawan", "Upload & Export Data Karyawan"])

    # ---------------- Tab 1: Dashboard (Read-only) ----------------
    with tab1:
        st.subheader("📊 Dashboard – Mini MCU (Nurse View)")

        from db.helpers import get_dashboard_checkup_data, get_all_lokasi

        # --- Fetch combined employee + latest checkup data ---
        df_combined = get_dashboard_checkup_data()
        if df_combined is None or df_combined.empty:
            df_combined = pd.DataFrame()
            st.info("Belum ada data karyawan atau checkup yang tersedia.")

        # --- Fill missing medical columns ---
        medical_cols = ['tanggal_checkup','tinggi','berat','bmi','lingkar_perut',
                        'gula_darah_puasa','gula_darah_sewaktu','cholesterol','asam_urat']
        for col in medical_cols:
            if col not in df_combined.columns:
                df_combined[col] = None

        # --- Ensure tanggal_checkup is date ---
        if 'tanggal_checkup' in df_combined.columns:
            df_combined['tanggal_checkup'] = pd.to_datetime(df_combined['tanggal_checkup'], errors='coerce').dt.date
            if "tahun" not in df_combined.columns:
                df_combined["tahun"] = pd.to_datetime(df_combined["tanggal_checkup"], errors='coerce').dt.year
            if "bulan" not in df_combined.columns:
                df_combined["bulan"] = pd.to_datetime(df_combined["tanggal_checkup"], errors='coerce').dt.month

        # --- Calculate status ---
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

        #subtab 1 : Riwayat Checkup Karyawan
        with tab1:
            st.subheader("📊 Dashboard – Mini MCU (Read-Only)")

            from db.helpers import get_dashboard_checkup_data, get_all_lokasi

            # --- Fetch combined employee + latest checkup data ---
            try:
                df_combined = get_dashboard_checkup_data()
            except Exception as e:
                st.error(f"❌ Gagal ambil data checkup: {e}")
                df_combined = pd.DataFrame()

            if df_combined.empty:
                st.info("Belum ada data karyawan atau checkup yang tersedia.")
            else:
                # --- Prepare month/year for filters ---
                month_names = ["All","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug",
                            "Sep","Oct","Nov","Dec"]
                try:
                    lokasi_options = sorted(set(get_all_lokasi()) | set(df_combined['lokasi'].dropna().tolist()))
                except Exception:
                    lokasi_options = sorted(set(df_combined['lokasi'].dropna().tolist()))
                status_options = ["Well","Unwell"]

                col1, col2, col3, col4 = st.columns([1,1,2,1])
                with col1:
                    filter_bulan = st.selectbox(
                        "Filter Bulan",
                        options=range(0,13),
                        index=0,
                        format_func=lambda x: month_names[x],
                        key="nurse_dashboard_filter_bulan"
                    )
                with col2:
                    years = sorted([int(y) for y in df_combined['tahun'].dropna().unique()])
                    filter_tahun = st.selectbox(
                        "Filter Tahun",
                        options=[0] + years,
                        index=0,
                        format_func=lambda x: "All" if x==0 else str(x),
                        key="nurse_dashboard_filter_tahun"
                    )
                with col3:
                    filter_lokasi = st.multiselect(
                        "Filter Lokasi",
                        options=lokasi_options,
                        default=lokasi_options,
                        key="nurse_dashboard_filter_lokasi"
                    )
                with col4:
                    filter_status = st.multiselect(
                        "Filter Status",
                        options=status_options,
                        default=status_options,
                        key="nurse_dashboard_filter_status"
                    )

                # --- Apply filters ---
                df_filtered = df_combined.copy()
                if filter_tahun != 0:
                    df_filtered = df_filtered[(df_filtered['tahun']==filter_tahun) | (df_filtered['tahun'].isna())]
                if filter_bulan != 0:
                    df_filtered = df_filtered[(df_filtered['bulan']==filter_bulan) | (df_filtered['bulan'].isna())]
                if filter_lokasi:
                    df_filtered = df_filtered[df_filtered['lokasi'].isin(filter_lokasi)]
                if filter_status:
                    df_filtered = df_filtered[df_filtered['status'].isin(filter_status) | df_filtered['status'].isna()]

                # --- Highlight unwell function ---
                def highlight_unwell(row):
                    styles = []
                    for col, v in row.items():
                        if col == "gula_darah_puasa": styles.append("color: red" if v>125 else "")
                        elif col == "gula_darah_sewaktu": styles.append("color: red" if v>199 else "")
                        elif col == "cholesterol": styles.append("color: red" if v>240 else "")
                        elif col == "asam_urat": styles.append("color: red" if v>7 else "")
                        elif col == "bmi": styles.append("color: red" if (v<18.5 or v>25) else "")
                        elif col == "lingkar_perut": styles.append("color: red" if v>90 else "")
                        else: styles.append("")
                    return styles

                # --- Columns to display ---
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
                    st.dataframe(
                        df_display.style
                            .format({
                                "tinggi":"{:.2f}","berat":"{:.2f}","bmi":"{:.2f}","lingkar_perut":"{:.2f}",
                                "gula_darah_puasa":"{:.2f}","gula_darah_sewaktu":"{:.2f}",
                                "cholesterol":"{:.2f}","asam_urat":"{:.2f}"
                            })
                            .apply(highlight_unwell, axis=1),
                        use_container_width=True
                    )


        #subtab 2 : Graph Placeholder
        with subtab2:
            st.info("📊 Graph placeholder – to be implemented later")

    # ---------------------- Tab 2: Data Karyawan ----------------------
    with tab2:
        st.subheader("👥 Pilih Data Karyawan")

        try:
            employees = get_employees()
        except Exception as e:
            st.error(f"❌ Gagal memuat daftar karyawan: {e}")
            employees = pd.DataFrame()

        # --- Build UID & Names ---
        uids, names = [], []
        if not employees.empty:
            uid_col = next((c for c in ["uid", "employee_uid", "id", "nik"] if c in employees.columns), None)
            name_col = next((c for c in ["nama", "name"] if c in employees.columns), None)
            if uid_col and name_col:
                uids = employees[uid_col].astype(str).tolist()
                names = employees[name_col].astype(str).tolist()

        display_options = ["-- Pilih Karyawan --"] + names

        col_sel, col_conf, col_res = st.columns([4, 1, 1])
        selected_name = col_sel.selectbox(
            "Pilih Karyawan",
            display_options,
            index=0,
            key=f"nurse_selector_{st.session_state['nurse_tab_form_counter']}"
        )
        confirm = col_conf.button("Konfirmasi Pilihan", use_container_width=True)
        reset = col_res.button("Reset Pilihan", use_container_width=True)

        if confirm:
            if selected_name == "-- Pilih Karyawan --" or selected_name == "":
                st.warning("⚠️ Pilih karyawan terlebih dahulu sebelum konfirmasi!")
            else:
                try:
                    idx = names.index(selected_name)
                    selected_uid = uids[idx]
                    st.session_state["nurse_selected_emp_uid"] = selected_uid
                    st.session_state["nurse_emp_locked"] = True
                    emp_raw = get_employee_by_uid(selected_uid)
                    emp = emp_raw.to_dict() if hasattr(emp_raw, "to_dict") else emp_raw
                    st.session_state["nurse_selected_employee_record"] = emp
                    st.success(f"✅ Karyawan dikunci: {selected_name}")
                except Exception as e:
                    st.error(f"❌ Gagal ambil data karyawan: {e}")

        if reset:
            st.session_state["nurse_selected_emp_uid"] = None
            st.session_state["nurse_emp_locked"] = False
            if "nurse_selected_employee_record" in st.session_state:
                del st.session_state["nurse_selected_employee_record"]
            st.session_state["nurse_tab_form_counter"] += 1
            st.info("🔄 Pilihan karyawan dan form direset.")
            st.rerun()

        emp = st.session_state.get("nurse_selected_employee_record", None)
        selected_uid = st.session_state.get("nurse_selected_emp_uid", None)

        # --- Permanent subtabs ---
        tab_profil, tab_edit = st.tabs(["Profil Karyawan", "Edit Data Karyawan"])

        # ---------------------- Profil Karyawan ----------------------
        with tab_profil:
            if emp:
                st.markdown(f"**Nama:** {emp.get('nama','')}")
                st.markdown(f"**Tanggal Lahir:** {pd.to_datetime(emp.get('tanggal_lahir',''), errors='coerce').strftime('%Y-%m-%d') if emp.get('tanggal_lahir') else ''}")
                st.markdown(f"**Lokasi:** {emp.get('lokasi','')}")
                st.markdown(f"**Jabatan:** {emp.get('jabatan','')}")

                # Emergency contact
                current_contact = emp.get("kontak_darurat", "-") or "-"
                new_contact = st.text_input("Kontak Darurat", value=current_contact, key="kontak_darurat_input")
                if st.button("💾 Save Kontak Darurat", key="save_kontak_darurat"):
                    emp["kontak_darurat"] = new_contact
                    df = pd.DataFrame([emp])
                    save_manual_karyawan_edits(df)
                    st.success("✅ Emergency contact updated!")

                # Fetch all checkups
                all_checkups = get_medical_checkups_by_uid(emp["uid"])
                if not all_checkups.empty:
                    all_checkups["tanggal_checkup"] = pd.to_datetime(all_checkups["tanggal_checkup"], errors="coerce")

                    # Latest checkup
                    latest_df = all_checkups.sort_values("tanggal_checkup", ascending=False).head(1)
                    st.markdown("### 📌 Pemeriksaan Terakhir")

                    def highlight_unwell(row):
                        styles = []
                        for col, v in row.items():
                            if col == "gula_darah_puasa": styles.append("color: red" if v>125 else "")
                            elif col == "gula_darah_sewaktu": styles.append("color: red" if v>199 else "")
                            elif col == "cholesterol": styles.append("color: red" if v>240 else "")
                            elif col == "asam_urat": styles.append("color: red" if v>7 else "")
                            elif col == "bmi": styles.append("color: red" if (v<18.5 or v>25) else "")
                            elif col == "lingkar_perut": styles.append("color: red" if v>90 else "")
                            else: styles.append("")
                        return styles

                    st.dataframe(
                        latest_df.style
                        .format({
                            "tinggi":"{:.2f}","berat":"{:.2f}","bmi":"{:.2f}","lingkar_perut":"{:.2f}",
                            "gula_darah_puasa":"{:.2f}","gula_darah_sewaktu":"{:.2f}",
                            "cholesterol":"{:.2f}","asam_urat":"{:.2f}"
                        })
                        .apply(highlight_unwell, axis=1),
                        use_container_width=True
                    )

                    # Full history
                    st.markdown("### 📜 Riwayat Pemeriksaan")
                    history_df = all_checkups.sort_values("tanggal_checkup", ascending=False)
                    st.dataframe(
                        history_df.style
                        .format({
                            "tinggi":"{:.2f}","berat":"{:.2f}","bmi":"{:.2f}","lingkar_perut":"{:.2f}",
                            "gula_darah_puasa":"{:.2f}","gula_darah_sewaktu":"{:.2f}",
                            "cholesterol":"{:.2f}","asam_urat":"{:.2f}"
                        })
                        .apply(highlight_unwell, axis=1),
                        use_container_width=True
                    )
                else:
                    st.info("Belum ada data pemeriksaan medis.")
            else:
                st.info("Pilih karyawan terlebih dahulu untuk melihat profil.")

        # ---------------------- Edit Data Karyawan ----------------------
        with tab_edit:
            if emp:
                tanggal_check = st.date_input("Tanggal Pemeriksaan", datetime.today())
                col1, col2 = st.columns(2)
                tinggi = col1.number_input("Tinggi (cm)", value=float(emp.get("tinggi",0)))
                berat = col2.number_input("Berat (kg)", value=float(emp.get("berat",0)))
                bmi = round(berat/((tinggi/100)**2),2) if tinggi>0 else 0
                st.text_input("BMI", value=str(bmi), disabled=True)
                lingkar_perut = st.number_input("Lingkar Perut (cm)", value=float(emp.get("lingkar_perut",0)))
                gula_darah_puasa = st.number_input("Gula Darah Puasa", value=float(emp.get("gula_darah_puasa",0)))
                gula_darah_sewaktu = st.number_input("Gula Darah Sewaktu", value=float(emp.get("gula_darah_sewaktu",0)))
                cholesterol = st.number_input("Cholesterol", value=float(emp.get("cholesterol",0)))
                asam_urat = st.number_input("Asam Urat", value=float(emp.get("asam_urat",0)))

                if st.button("💾 Simpan Pemeriksaan"):
                    df = pd.DataFrame([{
                        "uid": selected_uid,
                        "tanggal_checkup": tanggal_check,
                        "tinggi": tinggi,
                        "berat": berat,
                        "bmi": bmi,
                        "lingkar_perut": lingkar_perut,
                        "gula_darah_puasa": gula_darah_puasa,
                        "gula_darah_sewaktu": gula_darah_sewaktu,
                        "cholesterol": cholesterol,
                        "asam_urat": asam_urat
                    }])
                    insert_medical_checkup(df)
                    st.success("✅ Pemeriksaan medis berhasil disimpan.")
            else:
                st.info("Pilih karyawan terlebih dahulu untuk menambahkan pemeriksaan.")

    # ---------------------- Tab 3: Upload & Export Data Checkup ----------------------
    with tab3:
        st.subheader("📂 Download / Upload Data Checkup")

        subtab1, subtab2 = st.tabs(["Download Data Checkup", "Upload Medical Checkup"])

        # ---------------- Subtab 1: Download Data Checkup & Template ----------------
        with subtab1:
            st.markdown("### 📥 Download Data Check-Up & Template")
            from utils.export_utils import generate_karyawan_template_excel, export_checkup_data_excel
            from db.helpers import get_dashboard_checkup_data

            # --- Lokasi filter for template ---
            try:
                employees_df = get_employees()
                lokasi_options = sorted(set(employees_df['lokasi'].dropna().tolist()))
            except Exception:
                lokasi_options = []

            filter_lokasi_template = st.multiselect(
                "Filter Lokasi untuk Template (opsional)",
                options=lokasi_options,
                default=lokasi_options,
                key="filter_lokasi_template_nurse"
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
                key="filter_lokasi_export_nurse_subtab1"
            )

            # --- Optional date filter for exporting actual checkup data ---
            selected_date = st.date_input(
                "Filter Export Berdasarkan Tanggal Checkup (opsional)",
                value=None,
                key="export_checkup_date_picker_nurse"
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


        # ---------------- Subtab 2: Upload Medical Checkup ----------------
        with subtab2:
            st.markdown("### 📁 Upload Data Medical Check-Up")

            uploaded_medical_file = st.file_uploader(
                "Upload file Data Medical Checkup", 
                type=["xls", "xlsx"], key="medical_upload_nurse_subtab"
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
