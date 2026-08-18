# Hillstone Job API

FastAPI service ที่ทำหน้าที่ export threat logs จากเครื่อง **Hillstone BDS** แล้วนำเข้าฐานข้อมูล **PostgreSQL** โดยอัตโนมัติ พร้อม Excel VBA เป็นหน้าต่างเรียกใช้งานสำหรับผู้ใช้ทั่วไป

---

## โปรเจกต์นี้คืออะไร

ระบบภายในสำหรับดึงรายงาน threat log รายวันจาก Hillstone BDS Appliance (`http://10.0.32.161/HomeApp/`) แล้วนำเข้า table `logs_cyber` บน PostgreSQL เพื่อใช้ในงาน SOC / threat analytics ต่อ

ปัญหาที่แก้:

* การ export log ผ่านหน้าเว็บ Hillstone ต้องคลิกหลายขั้นตอน และไม่สามารถตั้งเวลาอัตโนมัติได้
* การนำเข้า CSV เข้า PostgreSQL ต้องทำซ้ำด้วยมือ
* ผู้ใช้อยากเรียกงานจาก Excel (ที่ใช้งานประจำ) โดยไม่ต้อง SSH เข้าเครื่อง API

แนวทาง:

* ใช้ **Playwright** automate การ login + filter + export CSV จากหน้าเว็บ Hillstone
* ใช้ **Pandas + SQLAlchemy** แปลง CSV เป็น schema กลาง แล้ว insert เข้า PostgreSQL
* ห่อทั้งสองงานด้วย **FastAPI** พร้อม job queue และ log ต่องาน
* ใช้ **Excel VBA** (`.bas`) เป็นปุ่มเรียก API จากฝั่งผู้ใช้

---

## ความสามารถหลัก

* `POST /jobs/export-hillstone` — สั่งให้ Playwright ไป export CSV จาก Hillstone BDS
* `POST /jobs/insert-log` — อ่าน `LogsHillstoneDaily.csv` แล้ว insert เข้า PostgreSQL
* `GET  /jobs/{job_id}` — ดูสถานะของงาน (`queued` / `running` / `succeeded` / `failed`)
* `GET  /jobs/{job_id}/log` — ดาวน์โหลดไฟล์ log ของงาน
* `GET  /files/logs-hillstone.csv` — ดาวน์โหลด CSV ล่าสุด (รองรับทั้งไฟล์ดิบ, `.tar`, และ `.tar.gz`)
* `GET  /health` — health check
* `GET  /docs` — Swagger UI อัตโนมัติ

หมายเหตุด้าน concurrency: ระบบรับได้ทีละ 1 job ต่อประเภท และมี `ThreadPoolExecutor` 2 workers รองรับ export กับ insert พร้อมกัน

---

## โครงสร้างโปรเจกต์

```text
threat_hillstone/
├── api.py                       # FastAPI app (port 12010)
├── Job_export_hillstone.py      # Playwright: login → filter → export CSV
├── insert_log.py                # Pandas → SQLAlchemy → PostgreSQL
├── test_api_jobs.py             # Python client ทดสอบ API
├── test.py                      # สคริปต์ทดสอบแบบ ad-hoc
├── ImportCSVFromAPI.bas         # Excel VBA: ดาวน์โหลด CSV เข้า Sheet
├── RunHillstoneJobsFromAPI.bas  # Excel VBA: รัน export + insert จาก Excel
├── requirements.txt
├── .env.example                 # ตัวอย่างค่า env (Base64 encoded)
├── README.md
├── README_API.md                # รายละเอียด endpoint เพิ่มเติม
├── AGENTS.md                    # กฎสำหรับ AI agent
├── docs/
│   ├── project_rules.md
│   └── user_rules.md
└── job_logs/                    # log ต่องาน (สร้างตอนรัน)
```

---

## Technology Stack

| Layer            | เทคโนโลยี                                        |
| ---------------- | ----------------------------------------------- |
| API Server       | FastAPI + Uvicorn                               |
| Browser Automate | Playwright (Chromium, headless)                 |
| Data Processing  | Pandas                                          |
| Database         | PostgreSQL (ผ่าน SQLAlchemy + psycopg2-binary)  |
| Config           | python-dotenv (Base64 encoded credentials)      |
| Frontend Client  | Excel VBA macros (`.bas`)                        |
| Python           | 3.x (ดู `requirements.txt`)                      |

---

## Requirements

* Python 3.10+
* PostgreSQL ที่มี database ปลายทางและสิทธิ์ INSERT บนตาราง `logs_cyber`
* Network access ไปยัง Hillstone BDS Appliance (`http://10.0.32.161/HomeApp/`)
* Chromium ติดตั้งผ่าน `playwright install chromium`
* Windows (สำหรับ Excel VBA macros)

---

## Installation

```powershell
git clone <repository>
cd threat_hillstone

python -m pip install -r requirements.txt
python -m playwright install chromium
```

สร้างไฟล์ `.env` จาก `.env.example` แล้วกรอกค่าจริง:

```text
# ทุกค่าต้อง encode เป็น Base64 (UTF-8) ก่อนใส่
POSTGRES_USER_B64=
POSTGRES_PASSWORD_B64=
POSTGRES_HOST_B64=
POSTGRES_PORT_B64=
POSTGRES_DB_B64=
HILLSTONE_USERNAME_B64=
HILLSTONE_PASSWORD_B64=
HILLSTONE_HEADLESS=true
```

ตัวอย่างการ encode:

```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("my_password"))
```

---

## Configuration

ตัวแปรทั้งหมดอ่านจาก `.env` ผ่าน `python-dotenv` และต้องผ่านการ decode Base64 ที่ตัว script:

| ตัวแปร                  | ใช้โดย                       | ความหมาย                                     |
| ---------------------- | ---------------------------- | -------------------------------------------- |
| `HILLSTONE_USERNAME_B64` | `Job_export_hillstone.py` | ชื่อผู้ใช้ Hillstone BDS                     |
| `HILLSTONE_PASSWORD_B64` | `Job_export_hillstone.py` | รหัสผ่าน Hillstone BDS                       |
| `HILLSTONE_HEADLESS`     | `Job_export_hillstone.py` | `true` / `false` สำหรับโหมด headless        |
| `POSTGRES_USER_B64`      | `insert_log.py`           | PostgreSQL username                          |
| `POSTGRES_PASSWORD_B64`  | `insert_log.py`           | PostgreSQL password                          |
| `POSTGRES_HOST_B64`      | `insert_log.py`           | PostgreSQL host                              |
| `POSTGRES_PORT_B64`      | `insert_log.py`           | PostgreSQL port (ตัวเลข)                     |
| `POSTGRES_DB_B64`        | `insert_log.py`           | PostgreSQL database name                     |

**ห้าม** commit ไฟล์ `.env` ลง Git ดู `.gitignore`

---

## Development

รัน API server (development):

```powershell
python -m uvicorn api:app --host 0.0.0.0 --port 12010 --reload
```

หรือรันแบบ entrypoint:

```powershell
python api.py
```

เปิด Swagger UI: `http://localhost:12010/docs`

ทดสอบ end-to-end:

```powershell
python test_api_jobs.py --job all
```

---

## Excel VBA Usage

ผู้ใช้สามารถเรียก export / insert จาก Excel ได้โดยตรง

1. เปิด Excel → `Alt+F11` เพื่อเปิด VBA editor
2. `File` → `Import File` แล้วเลือก `RunHillstoneJobsFromAPI.bas`
3. แก้ค่า `API_URL` ในโมดูลให้ตรงกับเครื่อง server
4. รัน macro:
   * `Run_Python_Hillstone` — รัน export แล้วตามด้วย insert
   * `Run_Export_Hillstone_API` — รันเฉพาะ export
   * `Run_Insert_Log_API` — รันเฉพาะ insert

มาโครจะยิง API แล้ว poll สถานะทุก ๆ 5 วินาทีจนกว่างานจะจบ

ต้องการแค่ดาวน์โหลด CSV เข้า Sheet ให้ import `ImportCSVFromAPI.bas` แล้วรัน `ImportCSVToLogHillstone`

---

## Security

* API **ไม่มี authentication** — ทุก client ที่เข้าถึง port 12010 สั่งงานได้
  **ต้อง** จำกัด port `12010` ด้วย Windows Firewall ให้เฉพาะเครื่อง/วงที่ไว้ใจ
* Credentials ทุกตัวเก็บใน `.env` ในรูปแบบ **Base64** (เป็นการปิดบังเบื้องต้น ไม่ใช่ encryption)
* ห้าม log credentials, token, หรือข้อมูล sensitive ออกมา

---

## Troubleshooting

| อาการ                                              | สาเหตุที่พบบ่อย                                                       |
| -------------------------------------------------- | -------------------------------------------------------------------- |
| API ค้างที่สถานะ `running`                         | export job เดิมยังไม่จบ — รอ หรือตรวจ log ใน `job_logs/`              |
| `Insert Error` จาก `insert_log.py`                 | schema ของตาราง `logs_cyber` ไม่ตรง — ตรวจ column names                |
| โหลด CSV ไม่สำเร็จ                                  | ไฟล์อาจถูก lock จาก export รอบก่อน หรือโหลดไม่สมบูรณ์                 |
| Playwright login ไม่ผ่าน                            | `HILLSTONE_USERNAME_B64` / `HILLSTONE_PASSWORD_B64` ผิด หรือ base64 เสีย |
| `409 Conflict` ตอนดาวน์โหลด CSV                     | export job ยังไม่จบ — ตรวจ `GET /jobs/{job_id}`                      |
| `RuntimeError: Missing X in .env`                  | ลืมตั้งค่า env ตัวใดตัวหนึ่ง หรือ encode ไม่ถูก                        |

---

## Documentation

* [README_API.md](file:///c:/Users/user/Desktop/threat_hillstone/README_API.md) — ตัวอย่างการเรียก API ด้วย PowerShell
* [AGENTS.md](file:///c:/Users/user/Desktop/threat_hillstone/AGENTS.md) — กฎสำหรับ AI agent
* [docs/project_rules.md](file:///c:/Users/user/Desktop/threat_hillstone/docs/project_rules.md) — กฎของโปรเจกต์
* [docs/user_rules.md](file:///c:/Users/user/Desktop/threat_hillstone/docs/user_rules.md) — รูปแบบการทำงานที่เจ้าของชอบ
