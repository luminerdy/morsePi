import unittest

from scripts.apply_station_sync_policies import (
    build_policy,
    put_user_policy,
    snapshot_object_arns,
    student_object_arns,
)


class ApplyStationSyncPoliciesTests(unittest.TestCase):
    def test_policy_scopes_student_attempts_to_roster(self):
        policy = build_policy("example-bucket", ["astrid", "liara"])
        resources = policy["Statement"][2]["Resource"]

        self.assertEqual([
            "arn:aws:s3:::example-bucket/students/astrid/attempts/*",
            "arn:aws:s3:::example-bucket/students/liara/attempts/*",
        ], resources)
        self.assertNotIn(
            "arn:aws:s3:::example-bucket/students/campbell/attempts/*",
            resources,
        )

    def test_policy_reads_only_latest_progress_snapshot_objects(self):
        self.assertEqual([
            "arn:aws:s3:::example-bucket/stations/pappy-test-station/snapshots/latest_progress.json",
            "arn:aws:s3:::example-bucket/stations/astrid-liara-station/snapshots/latest_progress.json",
            "arn:aws:s3:::example-bucket/stations/campbell-olivea-station/snapshots/latest_progress.json",
        ], snapshot_object_arns("example-bucket"))

    def test_policy_has_no_delete_action(self):
        policy = build_policy("example-bucket", ["pappy"])
        actions = []
        for statement in policy["Statement"]:
            action = statement["Action"]
            if isinstance(action, list):
                actions.extend(action)
            else:
                actions.append(action)

        self.assertNotIn("s3:DeleteObject", actions)

    def test_dry_run_builds_put_user_policy_command(self):
        result = put_user_policy(
            "astrid-liara-station",
            {"user": "morsepi-astrid-liara-station", "students": ["astrid", "liara"]},
            "example-bucket",
            "setup-profile",
            dry_run=True,
            aws_executable="C:/tools/aws.cmd",
        )

        self.assertTrue(result["skipped"])
        self.assertEqual("C:/tools/aws.cmd", result["command"][0])
        self.assertIn("put-user-policy", result["command"])
        self.assertIn("morsepi-astrid-liara-station", result["command"])

    def test_station_policies_cover_all_manageable_family_operators(self):
        from scripts.apply_station_sync_policies import FAMILY_STUDENTS, STATIONS

        for station in STATIONS.values():
            self.assertEqual(FAMILY_STUDENTS, station["students"])

    def test_student_object_arns_include_attempt_prefix_only(self):
        self.assertEqual([
            "arn:aws:s3:::example-bucket/students/pappy/attempts/*",
        ], student_object_arns("example-bucket", ["pappy"]))


if __name__ == "__main__":
    unittest.main()
