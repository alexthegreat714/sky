import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.query_client import query_model


def main():
    print("Testing unified query_model() ...")
    result = query_model("ping")
    print(result)


if __name__ == "__main__":
    main()
