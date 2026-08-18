from pathlib import Path
from unittest import TestCase

from subtitle_maker.jobs.store import FileJobStore, JobNotFoundError


class JobStoreTest(TestCase):
    def test_store_round_trip(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            store = FileJobStore(Path(directory))
            created = store.create("episode.mp4")

            loaded = store.get(created.id)

            self.assertEqual(loaded, created)

    def test_store_rejects_non_uuid_job_id(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            store = FileJobStore(Path(directory))

            with self.assertRaises(JobNotFoundError):
                store.job_dir("../../outside")
