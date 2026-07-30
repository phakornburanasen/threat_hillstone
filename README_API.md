# Hillstone Job API

## Start the API

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Start FastAPI and listen on every network interface:

```powershell
python api.py
```

Open the interactive API documentation:

```text
http://SERVER_IP:12010/docs
```

The API does not require authentication. Restrict port 12010 to trusted
networks with Windows Firewall because any client that can reach the API can
start export and insert jobs.

Download the latest Hillstone CSV:

```text
GET http://SERVER_IP:12010/files/logs-hillstone.csv
```

The endpoint automatically decompresses a GZIP-formatted Hillstone export and
returns a normal CSV file. It returns HTTP 409 while an export job is still
running.

## API examples

Health check:

```powershell
Invoke-RestMethod -Method Get -Uri 'http://SERVER_IP:12010/health'
```

Start the Hillstone export:

```powershell
$job = Invoke-RestMethod -Method Post `
  -Uri 'http://SERVER_IP:12010/jobs/export-hillstone'
$job
```

Start the PostgreSQL insert:

```powershell
$job = Invoke-RestMethod -Method Post `
  -Uri 'http://SERVER_IP:12010/jobs/insert-log'
$job
```

Check job status:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://SERVER_IP:12010/jobs/$($job.job_id)"
```

Download the job log:

```powershell
Invoke-WebRequest -Method Get `
  -Uri "http://SERVER_IP:12010/jobs/$($job.job_id)/log" `
  -OutFile "$($job.job_id).log"
```

Run `export-hillstone` first and wait until its state is `succeeded` before
starting `insert-log`. Job history is kept in memory and resets when the API
process restarts. Log files remain in the `job_logs` directory.

## Python test client

Run export and wait for it to finish:

```powershell
python test_api_jobs.py --job export
```

Run insert and wait for it to finish:

```powershell
python test_api_jobs.py --job insert
```

Run export followed by insert:

```powershell
python test_api_jobs.py --job all
```

To test an API on another server:

```powershell
python test_api_jobs.py --job all --base-url http://10.0.32.100:12010
```

## Excel VBA import

Import `ImportCSVFromAPI.bas` into the Excel VBA project:

1. Open the VBA editor with `Alt+F11`.
2. Select `File` > `Import File`.
3. Select `ImportCSVFromAPI.bas`.
4. Run `ImportCSVToLogHillstone`.

Change the `API_URL` constant in the VBA module when the API server IP or port
changes.

## Excel VBA job runner

Import `RunHillstoneJobsFromAPI.bas` into the Excel VBA project. Run:

- `Run_Python_Hillstone` to run export and then insert.
- `Run_Export_Hillstone_API` to run only export.
- `Run_Insert_Log_API` to run only insert.

The VBA module starts each API job and polls its status every five seconds.
