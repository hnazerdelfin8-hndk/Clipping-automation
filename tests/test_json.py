import json


def test_json_round_trip():
    payload = {"status": "ok", "format": "json", "html": False}
    text = json.dumps(payload)
    assert json.loads(text) == payload
