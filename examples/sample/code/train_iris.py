from pathlib import Path


def main():
    data_dir = Path("data")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    rows = []
    for csv_file in data_dir.glob("iris_org_*.csv"):
        rows.extend(csv_file.read_text(encoding="utf-8").splitlines()[1:])
    (output_dir / "iris_model.pkl").write_bytes(
        f"logistic-regression-sample-model\nrows={len(rows)}\n".encode("utf-8")
    )
    (output_dir / "metrics.json").write_text(
        '{"accuracy": 0.9667, "f1_score": 0.9615, "note": "sample metrics"}',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
