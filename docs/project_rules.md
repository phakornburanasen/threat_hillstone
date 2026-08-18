# Project Rules — Hillstone Job API

กฎเฉพาะของโปรเจกต์นี้ ใช้ร่วมกับ `AGENTS.md` และ `docs/user_rules.md`

เมื่อกฎขัดแย้งกัน ให้ยึดลำดับความสำคัญ: **Security > Project rules > User preferences**

---

## 1. ขอบเขตของโปรเจกต์

ระบบมี 2 งานหลักที่รันผ่าน FastAPI:

* **export-hillstone** — Playwright automate หน้าเว็บ Hillstone BDS (`http://10.0.32.161/HomeApp/`) เพื่อ export CSV เป็น `LogsHillstoneDaily.csv`
* **insert-log** — อ่าน CSV แล้ว insert เข้า table `logs_cyber` บน PostgreSQL

งานทั้งสองรันเป็น **subprocess** ผ่าน `subprocess.run` ใน `api.py` โดยมี `ThreadPoolExecutor` จำกัด 2 workers

ห้ามเพิ่มงาน/endpoint ใหม่ที่ไม่เกี่ยวกับ workflow นี้โดยไม่ได้รับอนุมัติ

---

## 2. โครงสร้างไฟล์ที่ห้ามเปลี่ยน

* `api.py` — เป็นจุดเดียวที่ประกาศ `FastAPI()` และ job runner
* `Job_export_hillstone.py` — script ของ `export_hillstone` job
* `insert_log.py` — script ของ `insert_log` job
* `ImportCSVFromAPI.bas`, `RunHillstoneJobsFromAPI.bas` — Excel VBA ที่ผู้ใช้ import เข้า Excel

ชื่อ script ต้องตรงกับ key ใน `SCRIPTS` dict ใน `api.py` มิเช่นนั้น API จะสั่งงานไม่ได้

---

## 3. กฎการตั้งชื่อ

* Python: ใช้ `snake_case` สำหรับ module, function, variable — ตาม PEP 8
* `api.py` ตั้งชื่อ constant ด้วย `UPPER_CASE` (`CSV_FILE`, `LOG_DIR`, `SCRIPTS`, `JobName`, `JobState`)
* FastAPI endpoint ใช้ kebab-case ใน path เช่น `/jobs/export-hillstone`, `/jobs/insert-log`, `/files/logs-hillstone.csv`
* VBA: ใช้ `PascalCase` สำหรับ `Sub` เช่น `Run_Python_Hillstone`, `ImportCSVToLogHillstone`
* ค่า config ใน `.env` ที่เก็บ credential ให้ลงท้ายด้วย `_B64`

---

## 4. กฎเรื่อง Credentials และ Configuration

* **ทุก** credential (Hillstone + PostgreSQL) ต้องเก็บใน `.env` ในรูปแบบ Base64 ผ่าน helper `decode_env_base64()` ในแต่ละ script
* ไฟล์ `.env` ห้าม commit — มี `.env.example` เป็น template ที่ไม่มีค่าจริง
* ห้าม log ค่า env ออกมา ไม่ว่ากรณีใด ๆ
* ห้าม hardcode username/password ใน source code
* `HILLSTONE_HEADLESS` ตั้งค่าเริ่มต้นเป็น `"true"` ใน `.env.example` ใช้ตอน production หากต้อง debug ด้วยตา ให้เปลี่ยนเป็น `"false"` ชั่วคราว

---

## 5. กฎเรื่อง CSV และไฟล์

* ไฟล์ CSV ที่ใช้ร่วมกันคือ `LogsHillstoneDaily.csv` ที่ root ของโปรเจกต์
* โครงสร้าง CSV ที่คาดหวัง (column headers):

  ```text
  Threat Name, Threat Type, Threat Subtype, Severity,
  Source, Port, Destination, Port.1,
  Source Interface, Destination Interface,
  Application/Protocol, Action,
  Attack Start Time, Attack End Time,
  Detected by, Addition Info
  ```

* รองรับทั้ง plain CSV, GZIP (`.csv.gz`), และ TAR archive (`.tar`, `.tar.gz`) — ตรวจด้วย `tarfile.is_tarfile` และ magic bytes `\x1f\x8b`
* หาก column แรกไม่ใช่ `Threat Name` ให้ rename เป็น `Threat Name` (เป็นพฤติกรรมเดิมของ `insert_log.py` ห้ามลบ)
* `addition_by` (จาก `Addition Info`) ต้อง truncate ที่ 255 ตัวอักษรก่อน insert
* Port columns (`source_port`, `destination_port`) ให้ `pd.to_numeric(errors='coerce')` เพื่อกัน string ปน
* Datetime columns (`attack_start_time`, `attack_end_time`) format ที่คาดหวังคือ `%Y/%m/%d %H:%M:%S` ใช้ `errors='coerce'`

---

## 6. กฎเรื่อง Playwright / Browser Automation

* Target URL: `http://10.0.32.161/HomeApp/` (hardcode ใน script — ห้ามดึงจาก env จนกว่าจะมีเหตุต้องเปลี่ยน)
* ใช้ `expect(...)` แทน `wait_for_timeout` ยกเว้นกรณีที่ต้องรอ animation
* XPath ที่ใช้ในปัจจุบัน (`/html/body/div[4]/div/li[3]`, ฯลฯ) เปราะบาง — เมื่อ UI Hillstone เปลี่ยน ให้ปรับทันทีและบันทึกเหตุผล
* ExtJS มีปุ่ม `OK` หลายปุ่มซ่อนอยู่ — ใช้ `span.x-btn-inner:visible` filter แทน ID ตามที่ `Job_export_hillstone.py` ทำอยู่
* Screenshot debug เก็บใน folder `log pic/` (สร้างอัตโนมัติ) ใช้ช่วยวิเคราะห์ตอน login/export ไม่สำเร็จ

---

## 7. กฎเรื่อง API Job

* Endpoint รับได้ทีละ 1 job ต่อประเภท ถ้ามี job อื่นค้างอยู่ ตอบ `409 Conflict` ทันที
* Job state: `queued` → `running` → (`succeeded` | `failed`) ตามลำดับ
* Log ของแต่ละ job เก็บที่ `job_logs/{job_id}_{job_name}.log` ใช้ `PYTHONIOENCODING=utf-8` เพื่อกันปัญหาภาษาไทย
* Job history เก็บใน memory เท่านั้น — restart API แล้วหาย เป็นพฤติกรรมที่ยอมรับได้
* ห้ามเปลี่ยน schema ของ `Job` model โดยไม่อัปเดต VBA client ให้ตรงกัน

---

## 8. กฎเรื่อง Database

* Target table: `logs_cyber` ใช้ `if_exists='append'` ห้ามเปลี่ยนเป็น `replace` เด็ดขาด
* Insert แบ่ง chunk 1000 แถว ด้วย `chunksize=1000` ห้ามลด chunk size โดยไม่มีเหตุผล
* ตารางต้องมี column `created_at` (timestamp / timestamptz) เพื่อใช้กับ retention policy
* **Retention policy:** `insert_log.py` จะลบข้อมูลที่ `created_at < NOW() - INTERVAL '90 days'` ทุกครั้งที่รัน (cleanup pass) ห้ามเปลี่ยน 90 วัน หรือปิด cleanup โดยไม่ได้รับอนุมัติ
* **Dedup policy:** ก่อน insert ทุกครั้ง ให้เช็คว่ามี record ในตารางที่ `attack_start_time` อยู่ในช่วงเดียวกับข้อมูลที่จะ insert หรือไม่ (ค่า `min`/`max` ของคอลัมน์ `attack_start_time` ใน DataFrame) ถ้ามี → ข้าม insert
* `DELETE` อื่น ๆ นอกเหนือจาก retention pass ห้ามทำโดยพลการ
* ก่อนเปลี่ยน schema ให้ตรวจ column mapping ใน `insert_log.py` และตรวจ Excel VBA ที่อ้างถึง column ด้วย

---

## 9. กฎเรื่อง Network / Port

* API listen ที่ `0.0.0.0:12010`
* **API ไม่มี authentication** — ผู้ดูแลต้องจำกัด port ด้วย Windows Firewall ให้เฉพาะเครือข่ายที่ไว้ใจ
* หากต้อง expose ออกเน็ต ต้องใส่ reverse proxy + auth ก่อน
* ไฟล์ `Port 12010.txt` เก็บ reference ของการตั้งค่า firewall ใช้อ้างอิงเมื่อตั้งเครื่องใหม่

---

## 10. กฎเรื่อง Dependencies

* ใช้เฉพาะ dependency ใน `requirements.txt` เท่านั้น:

  ```text
  fastapi==0.124.4
  uvicorn[standard]==0.30.6
  python-dotenv
  pandas
  sqlalchemy
  psycopg2-binary
  playwright
  ```

* ก่อนเพิ่ม dependency ใหม่ อธิบายเหตุผลใน commit message และตรวจว่าไม่มี package เดิมที่ทำได้
* Pin version เมื่อเป็นไปได้

---

## 11. กฎเรื่อง Testing

* `test_api_jobs.py` เป็น client ที่เรียก `export` แล้วรอ ก่อนเรียก `insert` — ต้องรัน export จนสำเร็จก่อนเสมอ
* ทดสอบด้วย `python test_api_jobs.py --job all` ก่อน push ทุกครั้ง
* ตอนทดสอบบนเครื่องอื่น ใช้ `--base-url http://SERVER:12010`
* ห้าม commit `LogsHillstoneDaily.csv` ที่เป็นข้อมูลจริง (ดู `.gitignore`)

---

## 12. กฎเรื่อง Logging

* ใช้ `print()` ใน script ย่อย (`Job_export_hillstone.py`, `insert_log.py`) เพราะ output จะถูก capture ลง log file ของ job
* ห้าม log credentials, token, หรือข้อมูลส่วนบุคคล
* ใน `api.py` ใช้ exception แล้วปล่อยให้ FastAPI จัดการ — ไม่ต้อง wrap ซ้อน

---

## 13. กฎเฉพาะที่ห้ามละเมิด

* ห้ามเปลี่ยน table ปลายทางจาก `logs_cyber`
* ห้ามเปลี่ยน port `12010` โดยไม่อัปเดต VBA client และไฟล์ `Port 12010.txt`
* ห้ามเปลี่ยน `LogsHillstoneDaily.csv` เป็นชื่ออื่น — VBA client อ้างถึงชื่อนี้
* ห้ามเปลี่ยน env variable name ที่ลงท้ายด้วย `_B64` โดยไม่อัปเดตทั้ง script และ `.env.example`
* ห้ามใส่ `check=True` ใน `subprocess.run` ใน `api.py` — ให้จัดการ `returncode` เอง เพื่อให้ job ไม่ raise และหยุด API

---

## 14. Change Policy

เมื่อต้องเปลี่ยนกฎ หรือเปลี่ยนพฤติกรรมที่ผู้ใช้/operator พึ่งพา:

1. อัปเดตไฟล์นี้
2. อัปเดต `README.md` / `README_API.md` ถ้ามีการเปลี่ยน API หรือ config
3. อัปเดต VBA macros ถ้ามีการเปลี่ยน response shape
4. แจ้งผู้ใช้ที่ import VBA ไปแล้วทุกคน
