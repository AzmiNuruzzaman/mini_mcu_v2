# utils/export_utils.py
import pandas as pd
from io import BytesIO
from db.queries import get_employees

def generate_karyawan_template_excel(lokasi_filter=None):
    """
    Generate Excel template for nurses/managers:
    - Auto-calculation: umur, bmi, BMI_category
    - Empty medical columns for manual entry
    - Optional filter by lokasi
    Returns: BytesIO object
    """
    # Fetch master data
    df = get_employees().copy()

    # Optional filter by lokasi
    if lokasi_filter:
        if isinstance(lokasi_filter, str):
            lokasi_filter = [lokasi_filter]
        df = df[df['lokasi'].isin(lokasi_filter)]

    # Ensure essential columns exist
    required_cols = ['uid','nama','jabatan','lokasi']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Add tanggal_checkup right after lokasi
    if 'tanggal_checkup' not in df.columns:
        df.insert(df.columns.get_loc('lokasi')+1, 'tanggal_checkup', None)

    # Ensure tanggal_lahir exists
    if 'tanggal_lahir' not in df.columns:
        df['tanggal_lahir'] = None

    # Add empty medical columns
    medical_cols = ['tinggi','berat','lingkar_perut','gula_darah_puasa',
                    'gula_darah_sewaktu','cholesterol','asam_urat']
    for col in medical_cols:
        if col not in df.columns:
            df[col] = None

    # Add auto-calculation columns
    df['umur'] = None
    df['bmi'] = None
    df['BMI_category'] = None

    # Prepare Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Template Data Check-Up")
        workbook = writer.book
        worksheet = writer.sheets['Template Data Check-Up']

        # Map column names to Excel letters
        col_letters = {col: chr(65 + idx) for idx, col in enumerate(df.columns)}

        # Apply formulas for each row (starting at row 2, 1-based indexing)
        for row_idx in range(2, len(df)+2):
            # umur = YEARFRAC(tanggal_lahir, TODAY())
            if 'tanggal_lahir' in col_letters and 'umur' in col_letters:
                worksheet.write_formula(
                    row_idx-1, df.columns.get_loc('umur'),
                    f'=IF(ISNUMBER({col_letters["tanggal_lahir"]}{row_idx}),INT(YEARFRAC({col_letters["tanggal_lahir"]}{row_idx},TODAY(),1)),"")'
                )
            # bmi = berat / (tinggi/100)^2
            if 'berat' in col_letters and 'tinggi' in col_letters and 'bmi' in col_letters:
                worksheet.write_formula(
                    row_idx-1, df.columns.get_loc('bmi'),
                    f'=IF({col_letters["tinggi"]}{row_idx}>0,{col_letters["berat"]}{row_idx}/(({col_letters["tinggi"]}{row_idx}/100)^2),0)'
                )
            # BMI_category
            if 'bmi' in col_letters and 'BMI_category' in col_letters:
                worksheet.write_formula(
                    row_idx-1, df.columns.get_loc('BMI_category'),
                    f'=IF({col_letters["bmi"]}{row_idx}<18.5,"Underweight",IF({col_letters["bmi"]}{row_idx}<25,"Ideal",IF({col_letters["bmi"]}{row_idx}<30,"Overweight","Obese")))'
                )

    output.seek(0)
    return output

def export_checkup_data_excel(df: pd.DataFrame) -> BytesIO:
    """
    Export given checkup DataFrame to Excel (BytesIO) for download.
    Auto-formats numeric columns to 2 decimals safely.
    """
    output = BytesIO()
    df_to_export = df.copy()

    # Format numeric columns to 2 decimals safely
    numeric_cols = ['tinggi','berat','bmi','lingkar_perut',
                    'gula_darah_puasa','gula_darah_sewaktu','cholesterol','asam_urat']
    for col in numeric_cols:
        if col in df_to_export.columns:
            df_to_export[col] = pd.to_numeric(df_to_export[col], errors='coerce').round(2)

    # Convert tanggal columns to string for Excel
    for col in df_to_export.columns:
        if 'tanggal' in col.lower():
            df_to_export[col] = pd.to_datetime(df_to_export[col], errors='coerce').dt.strftime("%Y-%m-%d")

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_to_export.to_excel(writer, index=False, sheet_name="Checkup Data")
        workbook = writer.book
        worksheet = writer.sheets["Checkup Data"]

        # Optional: apply simple formatting
        fmt = workbook.add_format({'num_format': '0.00'})
        for col in numeric_cols:
            if col in df_to_export.columns:
                col_idx = df_to_export.columns.get_loc(col)
                worksheet.set_column(col_idx, col_idx, 12, fmt)

    output.seek(0)
    return output


