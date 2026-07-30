import base64
import binascii
import os
import tarfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# =========================================
# PostgreSQL Config
# =========================================
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_FILE)


def decode_env_base64(variable_name: str) -> str:
    encoded_value = os.getenv(variable_name)
    if not encoded_value:
        raise RuntimeError(f"Missing {variable_name} in {ENV_FILE}")

    try:
        return base64.b64decode(
            encoded_value,
            validate=True,
        ).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise RuntimeError(
            f"{variable_name} is not valid Base64 UTF-8"
        ) from error


try:
    DB_USER = decode_env_base64("POSTGRES_USER_B64")
    DB_PASS = decode_env_base64("POSTGRES_PASSWORD_B64")
    DB_HOST = decode_env_base64("POSTGRES_HOST_B64")
    DB_PORT = int(decode_env_base64("POSTGRES_PORT_B64"))
    DB_NAME = decode_env_base64("POSTGRES_DB_B64")
except (RuntimeError, ValueError) as error:
    raise SystemExit(f"PostgreSQL configuration error: {error}")

# =========================================
# CSV FILE
# =========================================
CSV_FILE = Path(__file__).resolve().parent / "LogsHillstoneDaily.csv"

# =========================================
# READ CSV
# =========================================
try:
    if tarfile.is_tarfile(CSV_FILE):
        with tarfile.open(CSV_FILE, "r:*") as archive:
            csv_members = [
                member
                for member in archive.getmembers()
                if member.isfile() and member.name.lower().endswith(".csv")
            ]
            if not csv_members:
                raise ValueError("ไม่พบไฟล์ CSV ภายใน TAR archive")

            csv_stream = archive.extractfile(csv_members[0])
            if csv_stream is None:
                raise ValueError("ไม่สามารถอ่านไฟล์ CSV ภายใน TAR archive")

            with csv_stream:
                df = pd.read_csv(
                    csv_stream,
                    encoding="utf-8-sig",
                    low_memory=False,
                )
        print("ตรวจพบและแตกไฟล์ CSV จาก TAR/GZIP")
    else:
        with open(CSV_FILE, "rb") as csv_stream:
            is_gzip = csv_stream.read(2) == b"\x1f\x8b"

        df = pd.read_csv(
            CSV_FILE,
            encoding="utf-8-sig",
            compression="gzip" if is_gzip else None,
            low_memory=False,
        )

        if is_gzip:
            print("ตรวจพบไฟล์ CSV ที่บีบอัดแบบ GZIP")

    # Hillstone may use the export filename as the first column header.
    if "Threat Name" not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: "Threat Name"})

    print("โหลด CSV สำเร็จ")

except Exception as e:
    print(f"โหลด CSV ไม่สำเร็จ : {e}")
    raise SystemExit(1)

# =========================================
# REMOVE HEADER ROW IF EXISTS
# =========================================
df = df.iloc[:]

# =========================================
# SELECT COLUMN BY NAME
# =========================================
df = pd.DataFrame({
    'threat_name': df['Threat Name'],
    'threat_type': df['Threat Type'],
    'threat_subtype': df['Threat Subtype'],
    'severity': df['Severity'],

    'source_ip': df['Source'],
    'source_port': df['Port'],

    'destination_ip': df['Destination'],
    'destination_port': df['Port.1'],

    'source_interface': df['Source Interface'],
    'destination_interface': df['Destination Interface'],

    'application_protocol': df['Application/Protocol'],

    'action': df['Action'],

    'attack_start_time': df['Attack Start Time'],
    'attack_end_time': df['Attack End Time'],

    'detected_by': df['Detected by'],
    'addition_by': df['Addition Info']
})

# =========================================
# CONVERT DATETIME
# =========================================
df['attack_start_time'] = pd.to_datetime(
    df['attack_start_time'],
    format='%Y/%m/%d %H:%M:%S',
    errors='coerce'
)

df['attack_end_time'] = pd.to_datetime(
    df['attack_end_time'],
    format='%Y/%m/%d %H:%M:%S',
    errors='coerce'
)

# =========================================
# CLEAN PORT
# =========================================
df['source_port'] = pd.to_numeric(
    df['source_port'],
    errors='coerce'
)

df['destination_port'] = pd.to_numeric(
    df['destination_port'],
    errors='coerce'
)

# =========================================
# CLEAN NULL
# =========================================
df = df.where(pd.notnull(df), None)

# =========================================
# TRUNCATE LONG FIELDS
# =========================================
df['addition_by'] = df['addition_by'].astype(str).str[:255]

# =========================================
# SHOW DATA
# =========================================
print("\n===== DATA SAMPLE =====")
print(df.head())

# =========================================
# CONNECT PostgreSQL
# =========================================
try:
    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )
    engine = create_engine(database_url)

    print("\nเชื่อมต่อ PostgreSQL สำเร็จ")

except Exception as e:
    print(f"เชื่อมต่อ PostgreSQL ไม่สำเร็จ : {e}")
    raise SystemExit(1)

# =========================================
# INSERT DATABASE
# =========================================
try:
    df.to_sql(
        'logs_cyber',
        engine,
        if_exists='append',
        index=False,
        chunksize=1000
    )

    print("\nImport Success")

except Exception as e:
    print(f"\nImport Error : {e}")
    raise SystemExit(1)
