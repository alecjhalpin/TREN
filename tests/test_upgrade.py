from pathlib import Path
import sqlite3
import tempfile
import unittest
import upgrade

class UpgradeTests(unittest.TestCase):
    def test_upgrade_and_rollback_preserve_data_and_hosts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();(root/'app.py').write_text('old code')
            secret=b'private test pairing';(root/'data/pairing-code.txt').write_bytes(secret)
            (root/'allowed-hosts.txt').write_text('private.test')
            with sqlite3.connect(root/'data/assistant.sqlite') as c:
                c.execute('CREATE TABLE memories(content TEXT)');c.execute("INSERT INTO memories VALUES('existing memory')")
            before=(root/'data/assistant.sqlite').read_bytes()
            backup=upgrade.upgrade(root)
            self.assertEqual(before,(root/'data/assistant.sqlite').read_bytes())
            self.assertEqual(secret,(root/'data/pairing-code.txt').read_bytes())
            self.assertEqual('private.test',(root/'allowed-hosts.txt').read_text())
            upgrade.rollback(backup)
            self.assertEqual('old code',(root/'app.py').read_text())
            self.assertEqual(before,(root/'data/assistant.sqlite').read_bytes())
