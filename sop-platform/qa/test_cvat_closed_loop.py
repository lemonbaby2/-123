from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

_IMPORT_RUNTIME = tempfile.TemporaryDirectory()
os.environ["SOP_RUNTIME_DIR"] = _IMPORT_RUNTIME.name
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

    def test_cvat_task_jobs_returns_official_editor_url(self) -> None:
        os.environ["CVAT_TOKEN"] = "unit-test-token"
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {
                    "id": 456,
                    "stage": "annotation",
                    "state": "in progress",
                    "start_frame": 0,
                    "stop_frame": 629,
                    "assignee": {"username": "worker"},
                }
            ]
        }
        config = {"api_url": "http://cvat.internal", "url": "http://cvat.example"}
        with patch.object(server, "cvat_config", return_value=config), patch("requests.get", return_value=response) as get:
            jobs = server.cvat_task_jobs(123)
        self.assertEqual(jobs[0]["url"], "http://cvat.example/tasks/123/jobs/456")
        self.assertEqual(jobs[0]["stop_frame"], 629)
        self.assertEqual(jobs[0]["assignee"], "worker")
        self.assertEqual(get.call_args.kwargs["params"]["task_id"], 123)

    def test_training_catalog_links_accepted_video_to_dataset_version(self) -> None:
        tasks = [{"cvat_task_id": 41, "video_id": "video-accepted", "url": "http://cvat/tasks/41"}]
        versions = [{
            "version_id": "ann-v1",
            "task_id": 41,
            "video_id": "video-accepted",
            "annotation_count": 12,
            "review_status": "accepted",
        }]
        datasets = [{"dataset_id": "dataset-v1", "video_id": "video-accepted"}]
        videos = {"videos": [{"id": "video-accepted", "display_name": "已验收视频", "frames": 630, "duration_s": 46.0}]}
        annotations = [{"annotation_id": "a1", "review_status": "human_confirmed"}]
        with (
            patch.object(server, "db_cvat_tasks", return_value=tasks),
            patch.object(server, "db_cvat_annotation_versions", return_value=versions),
            patch.object(server, "dataset_versions", return_value=datasets),
            patch.object(server, "video_catalog", return_value=videos),
            patch.object(server, "manual_annotation_items", return_value=annotations),
            patch.object(server, "prelabel_inventory_by_video", return_value={"video-accepted": {"available": True, "sampled_frames": 21, "detection_count": 44, "candidate_count": 5}}),
        ):
            items = server.training_annotated_videos()
        self.assertEqual(items[0]["video_id"], "video-accepted")
        self.assertEqual(items[0]["annotation_count"], 12)
        self.assertTrue(items[0]["training_eligible"])
        self.assertEqual(items[0]["prelabel_detection_count"], 44)
        self.assertEqual(items[0]["dataset_versions"], ["dataset-v1"])
        self.assertIn("video-accepted", items[0]["thumbnail_url"])

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
