# ui/master_interface.py
import streamlit as st
import pandas as pd
from db import queries

# -------------------------
# Helper for formatting numeric columns
# -------------------------
def format_checkups(df):
    return df.style.format({
        "tinggi": "{:.2f}",
        "berat": "{:.2f}",
        "lingkar_perut": "{:.2f}",
        "bmi": "{:.2f}",
        "gestational_diabetes": "{:.2f}",
        "cholesterol": "{:.2f}",
        "asam_urat": "{:.2f}"
    })

# -------------------------
# Master Interface
# -------------------------
def master_interface():
    st.title("🛡️ Master Dashboard")

    tab1, tab2 = st.tabs(["1️⃣ Data Management", "2️⃣ User Management"])

    # ---------------- Tab 1: Data Management ----------------
    with tab1:
        st.subheader("📂 Riwayat Upload Master Karyawan")

        # Load batch history from DB
        history_df = queries.get_upload_history()

        if history_df.empty:
            st.info("Belum ada riwayat upload master karyawan.")
        else:
            st.dataframe(history_df, use_container_width=True)

            # Select batch to delete
            selected_batch = st.selectbox(
                "Pilih Batch untuk dihapus",
                options=history_df["upload_batch_id"]
            )
            if st.button("🗑️ Hapus Batch Terpilih"):
                try:
                    queries.delete_batch(selected_batch)
                    st.success(f"✅ Batch {selected_batch} berhasil dihapus.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menghapus batch: {e}")

            # Delete ALL batches
            if st.button("🗑️ Hapus Semua Batch"):
                if st.confirm("Apakah Anda yakin ingin menghapus semua batch?"):
                    try:
                        for bid in history_df["upload_batch_id"]:
                            queries.delete_batch(bid)
                        st.success("✅ Semua batch berhasil dihapus.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal menghapus semua batch: {e}")

    # ---------------- Tab 2: User Management ----------------
    with tab2:
        st.subheader("👥 Active Users Count")

        # Ensure roles match DB case
        manager_count = queries.count_users_by_role("Manager")
        nurse_count = queries.count_users_by_role("Tenaga Kesehatan")
        st.metric("Manager Users", manager_count)
        st.metric("Nurse Users", nurse_count)

        st.markdown("---")
        st.subheader("Tambah User Baru")
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["Manager", "Tenaga Kesehatan"])
            submit_user = st.form_submit_button("Add User")
            if submit_user:
                if new_username and new_password:
                    try:
                        queries.add_user(new_username, new_password, new_role)
                        st.success(f"✅ User {new_username} ditambahkan sebagai {new_role}!")
                        st.experimental_rerun()
                    except Exception as e:
                        if "unique" in str(e).lower():
                            st.error("⚠️ Username sudah ada!")
                        else:
                            st.error(f"❌ Error: {e}")
                else:
                    st.error("Username dan password wajib diisi!")

        st.markdown("---")
        st.subheader("Existing Users")
        users_df = queries.get_users()
        st.dataframe(users_df, use_container_width=True)

        # Delete a user
        with st.expander("Hapus User"):
            if not users_df.empty:
                del_username = st.selectbox(
                    "Pilih user untuk dihapus",
                    users_df["username"]
                )
                if st.button("Hapus User Terpilih"):
                    try:
                        queries.delete_user(del_username)
                        st.success(f"✅ User {del_username} berhasil dihapus.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal menghapus user: {e}")

        # Reset user password
        with st.expander("Reset Password User"):
            if not users_df.empty:
                reset_username = st.selectbox(
                    "Pilih user untuk reset password",
                    users_df["username"]
                )
                new_pw = st.text_input("Password baru", type="password", key="reset_pw")
                if st.button("Reset Password"):
                    if new_pw:
                        queries.reset_user_password(reset_username, new_pw)
                        st.success(f"✅ Password {reset_username} berhasil di-reset.")
                        st.experimental_rerun()
                    else:
                        st.error("Masukkan password baru untuk reset!")

        # Reset all passwords
        st.markdown("---")
        st.subheader("Reset Semua Password")
        default_pw = st.text_input("Password default", type="password", key="default_pw_all")
        if st.button("Reset Semua Password"):
            if default_pw:
                try:
                    for u in users_df["username"]:
                        queries.reset_user_password(u, default_pw)
                    st.success("✅ Semua password user berhasil di-reset.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Gagal mereset semua password: {e}")
            else:
                st.error("Masukkan password default!")
