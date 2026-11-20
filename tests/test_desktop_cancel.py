from pathlib import Path
import tempfile
import threading
import time
import unittest
from desktop_client import DesktopQueue


class CancelTests(unittest.TestCase):
    def test_cancel_all_stops_next_jobs_and_never_completes_active_file(self):
        root=Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='dropagil-test-',dir=root) as directory:
            base=Path(directory)
            one=base/'one.bin';two=base/'two.bin'
            one.write_bytes(b'abc');two.write_bytes(b'def')
            entered,release=threading.Event(),threading.Event()
            class FakeAPI:
                completions=0
                starts=0
                def request(self,method,path,data=None,headers=None):
                    if path=='/api/uploads':
                        self.starts+=1
                        return {'id':'test','offset':0}
                    if method=='PUT':
                        entered.set();release.wait(5)
                        return {'offset':3}
                    if path.endswith('/complete'):
                        self.completions+=1
                    return {'ok':True}
            api=FakeAPI();queue=DesktopQueue(base/'jobs.json',api)
            try:
                queue.add([str(one),str(two)])
                self.assertTrue(entered.wait(5))
                queue.control('cancel')
                self.assertTrue(all(j['state']=='cancelled' for j in queue.snapshot()))
                release.set()
                time.sleep(.1)
                self.assertEqual(api.completions,0)
                self.assertEqual(api.starts,1)
                self.assertEqual(one.read_bytes(),b'abc')
                self.assertEqual(two.read_bytes(),b'def')
            finally:
                release.set();queue.close();queue.worker.join(5)
