from utils.csv_loader import load_cases
from utils.validators import validate_dataset


def test_dataset_valid():
    cases = load_cases()
    res = validate_dataset(cases)
    assert res["ok"] is True, f"Dataset validation failed: {res['errors']}"
