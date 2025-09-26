# ui/qr_manager.py
import streamlit as st
import pandas as pd
import io, zipfile
from db.queries import load_checkups, get_users
import qrcode
from PIL import Image

# -------------------------------
# QR Utilities
# -------------------------------
def generate_qr_bytes(qr_data: str) -> bytes:
    """Generate QR code image in-memory and return as bytes."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

def display_qr_code(qr_data: str, title="QR Code"):
    """Display QR code in Streamlit."""
    qr_bytes = generate_qr_bytes(qr_data)
    st.subheader(title)
    st.image(qr_bytes, width=200)
    return qr_bytes

# -------------------------------
# QR Manager Interface
# -------------------------------
def qr_manager_interface():
    st.header("📱 QR Code Management")

    # --- Load data ---
    users_df = get_users()
    checkups_df = load_checkups()

    # --- Merge users with checkups to ensure we have UID ---
    karyawan_data = checkups_df[['uid', 'nama']].drop_duplicates()
    if karyawan_data.empty:
        st.warning("Belum ada data medical untuk karyawan.")
        st.info("Upload data medical karyawan terlebih dahulu.")
        return

    # --- Build display mapping from checkups UID ---
    display_to_uid = {f"{row['nama']} (UID: {row['uid']})": row['uid']
                      for _, row in karyawan_data.iterrows()}

    # --- Dropdown selection ---
    st.subheader("👥 Daftar Karyawan")
    selected_display = st.selectbox("Pilih Karyawan:", options=list(display_to_uid.keys()))
    if not selected_display:
        return

    selected_uid = display_to_uid[selected_display]
    selected_user = karyawan_data[karyawan_data['uid'] == selected_uid].iloc[0]
    selected_name = selected_user['nama']

    # --- Build static server URL for QR code ---
    server_url = "http://localhost:8501"  # ✅ Replace with your actual server URL
    qr_url = f"{server_url}/app_karyawan?uid={selected_uid}"

    # --- Display QR ---
    display_qr_code(qr_url, f"QR Code untuk {selected_name}")

    if st.button("📥 Download QR Code"):
        qr_bytes = generate_qr_bytes(qr_url)
        st.download_button(
            label="Download QR Code Image",
            data=qr_bytes,
            file_name=f"{selected_name}_qrcode.png",
            mime="image/png"
        )

    # --- Bulk QR Generation ---
    st.markdown("---")
    st.subheader("📦 Download Semua QR Codes")
    if st.button("Generate & Download All QR Codes"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w") as zf:
            for _, row in karyawan_data.iterrows():
                name = row['nama']
                uid = row['uid']
                qr_url = f"{server_url}/app_karyawan?uid={uid}"
                qr_bytes = generate_qr_bytes(qr_url)
                zf.writestr(f"{name}_qrcode.png", qr_bytes)
        st.download_button(
            label="Download ZIP of All QR Codes",
            data=zip_buffer.getvalue(),
            file_name="all_karyawan_qrcodes.zip",
            mime="application/zip"
        )
