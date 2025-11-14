import os
import time

from app import app


if __name__ == "__main__":
    port = int(os.environ.get("SKY_DIALOG_PORT", "6060"))
    print(f"[Sky Dialog] Starting on port {port}…")
    time.sleep(0.5)
    app.run(host="0.0.0.0", port=port)
