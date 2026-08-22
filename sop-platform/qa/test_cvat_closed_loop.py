from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

_IMPORT_RUNTIME = tempfile.TemporaryDirectory()
os.environ["SOP_RUNTIME_DIR"] = _IMPORT_RUNTIME.name

import server


class CvatClosedLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.original_paths = {
            "RUNTIME_ROOT": server.RUNTIME_ROOT,
            "ANNOTATION_DB_PATH": server.ANNOTATION_DB_PATH,
            "CVAT_ANNOTATION_ROOT": server.CVAT_ANNOTATION_ROOT,
            "CVAT_SYNC_JOB_ROOT": server.CVAT_SYNC_JOB_ROOT,
            "DATASET_BUILD_ROOT": server.DATASET_BUILD_ROOT,
            "REMOVABLE_IMPORT_ROOT": server.REMOVABLE_IMPORT_ROOT,
        }
        server.RUNTIME_ROOT = root
        server.ANNOTATION_DB_PATH = root / "annotations.sqlite3"
        server.CVAT_ANNOTATION_ROOT = root / "cvat_annotation_versions"
        server.CVAT_SYNC_JOB_ROOT = root / "cvat_sync_jobs"
        server.DATASET_BUILD_ROOT = root / "dataset_versions"
        server.REMOVABLE_IMPORT_ROOT = root / "removable_imports"
        server.initialize_annotation_db()

    def tearDown(self) -> None:
        os.environ.pop("SOP_CVAT_WEBHOOK_SECRET", None)
        os.environ.pop("CVAT_TOKEN", None)
        for name, value in self.original_paths.items():
            setattr(server, name, value)
        self.temporary.cleanup()

    def test_webhook_signature_and_task_resolution(self) -> None:
        body = b'{"event":"update:job"}'
        os.environ["SOP_CVAT_WEBHOOK_SECRET"] = "unit-test-secret"
        digest = hmac.new(b"unit-test-secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(server.cvat_webhook_signature_valid(body, f"sha256={digest}"))
        self.assertFalse(server.cvat_webhook_signature_valid(body + b" ", digest))
        self.assertEqual(
            server.cvat_webhook_task_id({"job": {"task": {"id": 42}}}),
            42,
        )
        self.assertEqual(
            server.cvat_webhook_review_status({"job": {"stage": "acceptance", "state": "completed"}}),
            "accepted",
        )

    def test_annotation_only_version_and_manifest_are_idempotent(self) -> None:
        labels = [{"id": 7, "name": "螺钉"}]
        annotations = {
            "version": 3,
            "tags": [{"frame": 0, "label_id": 7, "attributes": []}],
            "shapes": [
                {
                    "frame": 2,
                    "label_id": 7,
                    "type": "rectangle",
                    "points": [10, 20, 30, 40],
                    "attributes": [],
                }
            ],
            "tracks": [
                {
                    "id": 99,
                    "label_id": 7,
                    "shapes": [
                        {"frame": 4, "type": "rectangle", "points": [12, 20, 32, 40]},
                        {"frame": 8, "type": "rectangle", "points": [18, 20, 38, 40]},
                    ],
                }
            ],
        }
        first = server.persist_cvat_annotation_version(
            12, "video-test", annotations, labels, "update:job", "accepted"
        )
        second = server.persist_cvat_annotation_version(
            12, "video-test", annotations, labels, "update:task", "pending_review"
        )
        self.assertEqual(first["version_id"], second["version_id"])
        self.assertEqual(first["annotation_count"], 4)
        manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["review_status"], "accepted")
        self.assertTrue(manifest["training_eligible"])
        self.assertEqual([item["frame"] for item in manifest["entries"]], [0, 2, 4, 8])
        self.assertEqual(len(server.db_cvat_annotation_versions(12)), 1)

    def test_pull_uses_task_video_binding_and_persists_annotation_only(self) -> None:
        server.db_record_cvat_task(
            {"name": "测试任务", "video_id": "video-bound", "labels": ["螺钉"]},
            {"task_id": 88, "url": "http://cvat.test/tasks/88", "mode": "api", "status": "已创建"},
        )
        os.environ["CVAT_TOKEN"] = "unit-test-token"
        annotation_response = Mock()
        annotation_response.raise_for_status.return_value = None
        annotation_response.headers = {}
        annotation_response.content = b"{}"
        annotation_response.json.return_value = {
            "version": 2,
            "tags": [],
            "shapes": [{"frame": 5, "label_id": 3, "type": "rectangle", "points": [1, 2, 3, 4]}],
            "tracks": [],
        }
        labels_response = Mock()
        labels_response.raise_for_status.return_value = None
        labels_response.json.return_value = {"results": [{"id": 3, "name": "螺钉"}]}
        with patch("requests.get", side_effect=[annotation_response, labels_response]) as get:
            result = server.cvat_pull_annotations(88, event_name="update:job")
        self.assertEqual(result["video_id"], "video-bound")
        self.assertEqual(result["annotation_count"], 1)
        self.assertEqual(get.call_count, 2)
        self.assertTrue(Path(result["annotation_path"]).is_file())

    def test_active_sync_job_is_deduplicated(self) -> None:
        with patch.object(server.threading, "Thread") as thread:
            first = server.start_cvat_sync_job(77, "video-77", "update:job", "pending_review")
            second = server.start_cvat_sync_job(77, "video-77", "update:task", "pending_review")
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertTrue(second["deduplicated"])
        thread.assert_called_once()

    def test_dataset_builder_requires_reviewer_acceptance(self) -> None:
        annotations = {
            "version": 1,
            "tags": [],
            "shapes": [{"frame": 2, "label_id": 7, "type": "rectangle", "points": [1, 2, 3, 4]}],
            "tracks": [],
        }
        pending = server.persist_cvat_annotation_version(
            19, "video-pending", annotations, [{"id": 7, "name": "螺钉"}], "manual", "pending_review"
        )
        with self.assertRaisesRegex(ValueError, "Reviewer"):
            server.build_dataset_version(pending["version_id"], "ST01", "PCB")

    def test_dataset_builder_uses_annotation_only_manifest(self) -> None:
        annotations = {
            "version": 2,
            "tags": [],
            "shapes": [{"frame": 8, "label_id": 3, "type": "rectangle", "points": [10, 20, 30, 40]}],
            "tracks": [],
        }
        accepted = server.persist_cvat_annotation_version(
            21, "video-accepted", annotations, [{"id": 3, "name": "PCB"}], "update:job", "accepted"
        )
        dataset = server.build_dataset_version(accepted["version_id"], "ST-01", "PCB")
        self.assertTrue(dataset["training_eligible"])
        self.assertEqual(dataset["frame_cache_policy"], "on-demand-jpeg-not-persistent-png")
        self.assertTrue(Path(dataset["manifest_path"]).is_file())
        self.assertEqual(len(list(server.DATASET_BUILD_ROOT.rglob("*.png"))), 0)

    def test_removable_source_rejects_path_traversal(self) -> None:
        root = Path(self.temporary.name) / "media" / "DJI_POCKET3"
        root.mkdir(parents=True)
        outside = root.parent / "outside.mp4"
        outside.write_bytes(b"x" * 8192)
        inventory = [{"mountpoint": str(root)}]
        with patch.object(server, "removable_media_inventory", return_value=inventory):
            with self.assertRaisesRegex(ValueError, "路径无效"):
                server._allowed_removable_source(str(root), "../outside.mp4")


if __name__ == "__main__":
    unittest.main()
