from types import SimpleNamespace

import numpy as np
from roadeye.recorded.inference import Recognizer
from roadeye.recorded.processing import ocr_due


def test_exact_ocr_cadence_v2_preserves_old_policy():
    assert 2.4 - 1.8 < 0.6
    assert not ocr_due(2.4, 1.8, "recorded-onnx-v1")
    assert ocr_due(2.4, 1.8, "recorded-onnx-v2")
    assert not ocr_due(2.399, 1.8, "recorded-onnx-v2")


def test_physical_crop_ocr_is_rgb_uint8_and_documented_shape():
    captured = {}

    def run(names, values):
        captured.update(values)
        scores = np.zeros((1, 10, 37), dtype=np.float32)
        scores[:, :, 36] = 1
        return [scores]

    recognizer = object.__new__(Recognizer)
    recognizer.session = SimpleNamespace(run=run)
    crop = np.full((20, 80, 3), [10, 20, 30], dtype=np.uint8)
    assert recognizer.recognize(crop)["text"] == ""
    assert captured["input"].shape == (1, 64, 128, 3)
    assert captured["input"].dtype == np.uint8
    assert captured["input"][0, 0, 0].tolist() == [30, 20, 10]
