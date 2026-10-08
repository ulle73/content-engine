"""Thin client for the kie.ai unified async task API.

createTask (POST /api/v1/jobs/createTask) -> taskId
recordInfo (GET  /api/v1/jobs/recordInfo?taskId=...) -> poll until state == success
Output URLs live in data.resultJson (a JSON *string*) -> {"resultUrls": [...]}.
"""
import json
import time
import requests

import carousel_config as config

_HEADERS = {
    "Authorization": f"Bearer {config.KIE_API_KEY}",
    "Content-Type": "application/json",
}

_TERMINAL_OK = {"success"}
_TERMINAL_FAIL = {"fail"}


def create_task(model: str, inp: dict) -> str:
    """Create a task, return its taskId."""
    url = f"{config.KIE_BASE_URL}/api/v1/jobs/createTask"
    resp = requests.post(url, headers=_HEADERS, json={"model": model, "input": inp}, timeout=60)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") not in (200, 0) or "data" not in body or not body["data"].get("taskId"):
        raise RuntimeError(f"createTask failed for {model}: {body}")
    return body["data"]["taskId"]


def get_task(task_id: str) -> dict:
    url = f"{config.KIE_BASE_URL}/api/v1/jobs/recordInfo"
    resp = requests.get(url, headers=_HEADERS, params={"taskId": task_id}, timeout=60)
    resp.raise_for_status()
    return resp.json().get("data", {})


def wait_for_result(task_id: str, label: str = "") -> str:
    """Poll until success; return the first output URL. Raises on failure/timeout."""
    deadline = time.monotonic() + config.POLL_TIMEOUT
    last_state = None
    while time.monotonic() < deadline:
        data = get_task(task_id)
        state = (data.get("state") or "").lower()
        if state != last_state:
            print(f"  [{label or task_id}] state={state}")
            last_state = state
        if state in _TERMINAL_OK:
            result_json = data.get("resultJson") or "{}"
            try:
                urls = json.loads(result_json).get("resultUrls", [])
            except json.JSONDecodeError:
                raise RuntimeError(f"[{label}] bad resultJson: {result_json!r}")
            if not urls:
                raise RuntimeError(f"[{label}] success but no resultUrls: {data}")
            return urls[0]
        if state in _TERMINAL_FAIL:
            raise RuntimeError(f"[{label}] task failed: {data.get('failMsg') or data.get('failCode') or data}")
        time.sleep(config.POLL_INTERVAL)
    raise TimeoutError(f"[{label}] task {task_id} did not finish within {config.POLL_TIMEOUT}s")


def run(model: str, inp: dict, label: str = "") -> str:
    """Create + wait; return output URL."""
    task_id = create_task(model, inp)
    print(f"  [{label or model}] taskId={task_id}")
    return wait_for_result(task_id, label=label)


def download(url: str, dest) -> str:
    """Download a URL to a local path."""
    dest = str(dest)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
    return dest
