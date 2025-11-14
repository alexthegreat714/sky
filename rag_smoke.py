import requests

B = "http://127.0.0.1:6010"


def main():
    resp = requests.post(f"{B}/rag/count", json={"where": {"source": "ops"}})
    resp.raise_for_status()
    data = resp.json()
    assert data.get("ok") is True and "count" in data, data

    export = requests.get(f"{B}/rag/export")
    export.raise_for_status()
    assert export.text.strip(), "export returned empty payload"

    print("ok")


if __name__ == "__main__":
    main()
