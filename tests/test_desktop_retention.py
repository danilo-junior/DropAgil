import json
from pathlib import Path
import tempfile
import threading
import unittest
from desktop_client import DesktopQueue
from runtime_paths import desktop_command


class RetentionTests(unittest.TestCase):
    def test_only_old_successful_rows_are_removed_without_touching_files(self):
        with tempfile.TemporaryDirectory() as folder:
            original=Path(folder)/'original.txt';original.write_text('keep')
            queue=DesktopQueue.__new__(DesktopQueue)
            queue.guard=threading.RLock();queue.path=Path(folder)/'jobs.json'
            queue.jobs=[{'id':'old','state':'done','finished':70,'source':str(original)},
                        {'id':'fresh','state':'done','finished':71},
                        {'id':'paused','state':'paused','finished':None},
                        {'id':'error','state':'error','finished':1},
                        {'id':'sending','state':'sending','finished':None}]
            queue.prune_finished(now=100)
            self.assertEqual([j['id'] for j in queue.jobs],['fresh','paused','error','sending'])
            self.assertEqual(original.read_text(),'keep')
            self.assertEqual(json.loads(queue.path.read_text()),queue.jobs)
            queue.prune_finished(now=101)
            self.assertEqual([j['id'] for j in queue.jobs],['paused','error','sending'])

    def test_shell_entrypoints_are_separate_and_preserve_paths(self):
        for mode in ('--send-network','--send-device'):
            command=desktop_command(mode,r'C:\folder with spaces\video.mp4')
            self.assertEqual(command[-2:], [mode,r'C:\folder with spaces\video.mp4'])
