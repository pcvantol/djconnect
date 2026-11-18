import json
import tempfile
import unittest
from pathlib import Path
from tools.verification.ghcr_publication_journal import PublicationJournal


class PublicationJournalTests(unittest.TestCase):
    def test_partial_attempt_is_preserved_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run.jsonl"
            journal = PublicationJournal(path, candidate_sha="a" * 40, manifest_digest="sha256:" + "b" * 64)
            journal.append("push_intent", tag="1.2.0")
            journal.append("push_confirmed", tag="1.2.0")
            journal.append("failure", tag="sha-a")
            journal.close()
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([event["event"] for event in events], ["start", "push_intent", "push_confirmed", "failure"])
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                PublicationJournal(path, candidate_sha="c" * 40, manifest_digest="sha256:" + "d" * 64)
            self.assertEqual(path.read_bytes(), original)

    def test_reject_symlink_and_unrecognized_event(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "target"
            target.write_text("preserve")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(FileExistsError):
                PublicationJournal(link, candidate_sha="a", manifest_digest="b")
            path = root / "new"
            journal = PublicationJournal(path, candidate_sha="a", manifest_digest="b")
            with self.assertRaises(ValueError):
                journal.append("untrusted", secret="not-recorded")
            journal.close()
            self.assertNotIn("not-recorded", path.read_text())
            self.assertEqual(target.read_text(), "preserve")
