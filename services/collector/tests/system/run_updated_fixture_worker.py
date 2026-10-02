from __future__ import annotations

import json
import os
import socket

from eye_collector.config import CollectorConfig
from eye_collector.sync.registry import AdapterRegistry
from eye_collector.sync.repository import SyncRepository
from eye_collector.sync.worker import SyncWorker


def main() -> int:
    if os.environ.get("P13_SYSTEM_TEST_MODE") != "true":
        raise RuntimeError("updated fixture worker is only available to the P13 system test")
    sync_url = os.environ["SYNC_DATABASE_URL"]
    etl_url = os.environ["ETL_DATABASE_URL"]
    repository = SyncRepository.connect(sync_url)
    worker = SyncWorker(
        repository,
        CollectorConfig.from_env(),
        etl_url,
        worker_id=f"p13-updated-{socket.gethostname()}",
        registry=AdapterRegistry.for_tests(fixture_revision="updated"),
    )
    processed = 0
    try:
        while worker.run_once():
            processed += 1
        print(json.dumps({"tasks_processed": processed}, separators=(",", ":")))
    finally:
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
