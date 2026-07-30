import argparse
import json
import time
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TERMINAL_STATES = {"succeeded", "failed"}


def api_request(
    base_url: str,
    method: str,
    path: str,
) -> Dict:
    request = Request(
        url=f"{base_url.rstrip('/')}{path}",
        method=method,
        headers={
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"API returned HTTP {error.code}: {response_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Cannot connect to API: {error.reason}") from error


def wait_for_job(
    base_url: str,
    job_id: str,
    poll_interval: float,
    timeout: float,
) -> Dict:
    deadline = time.monotonic() + timeout
    previous_state = None

    while time.monotonic() < deadline:
        job = api_request(
            base_url=base_url,
            method="GET",
            path=f"/jobs/{job_id}",
        )
        current_state = job["state"]

        if current_state != previous_state:
            print(f"Job {job_id}: {current_state}")
            previous_state = current_state

        if current_state in TERMINAL_STATES:
            return job

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Job {job_id} did not finish within {timeout:.0f} seconds"
    )


def run_job(
    base_url: str,
    job_name: str,
    poll_interval: float,
    timeout: float,
) -> bool:
    endpoint = {
        "export": "/jobs/export-hillstone",
        "insert": "/jobs/insert-log",
    }[job_name]

    print(f"\nStarting {job_name} job...")
    created_job = api_request(
        base_url=base_url,
        method="POST",
        path=endpoint,
    )
    job_id = created_job["job_id"]
    print(f"Created job_id: {job_id}")

    finished_job = wait_for_job(
        base_url=base_url,
        job_id=job_id,
        poll_interval=poll_interval,
        timeout=timeout,
    )

    print(json.dumps(finished_job, indent=2, ensure_ascii=False))
    print(f"Log endpoint: {base_url.rstrip('/')}/jobs/{job_id}/log")
    return finished_job["state"] == "succeeded"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test the Hillstone export and insert FastAPI jobs."
    )
    parser.add_argument(
        "--job",
        choices=("export", "insert", "all"),
        default="all",
        help="Job to test. 'all' runs export first, then insert.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:12010",
        help="FastAPI base URL.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between status checks.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1800.0,
        help="Maximum seconds to wait for each job.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    health = api_request(
        base_url=arguments.base_url,
        method="GET",
        path="/health",
    )
    print(f"API health: {health.get('status')}")

    jobs_to_run = (
        ("export", "insert")
        if arguments.job == "all"
        else (arguments.job,)
    )

    for job_name in jobs_to_run:
        succeeded = run_job(
            base_url=arguments.base_url,
            job_name=job_name,
            poll_interval=arguments.poll_interval,
            timeout=arguments.timeout,
        )
        if not succeeded:
            print(f"{job_name} failed; remaining jobs will not run.")
            return 1

    print("\nAll requested jobs succeeded.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, TimeoutError) as error:
        print(f"Test failed: {error}")
        raise SystemExit(1)
