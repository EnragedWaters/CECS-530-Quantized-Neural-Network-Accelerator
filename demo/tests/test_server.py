"""Exercise the real loopback HTTP interface without a browser or external requests."""
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from demo.server import make_server

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(0);cls.url=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def post(self,path,payload):
        request=Request(self.url+path,data=payload.encode(),headers={'Content-Type':'application/json'})
        return urlopen(request)
    def test_static_page_and_small_live_calculation(self):
        with urlopen(self.url) as response:self.assertIn(b'Inside our accelerator',response.read())
        with self.post('/api/simulate',json.dumps({'config':{'lanes':1}})) as response:r=json.load(response)
        self.assertEqual(r['output'],[[29]]);self.assertEqual(r['metrics']['total_cycles'],6)
    def test_private_paths_are_not_served(self):
        for path in ('/../.git/config','/_local/README.md','/assets/network.npz'):
            with self.assertRaises(HTTPError) as e:urlopen(self.url+path)
            self.assertEqual(e.exception.code,404)
    def test_invalid_settings_are_readable_errors(self):
        for payload in ('{"config":{"lanes":0}}','{"config":{"lanes":NaN}}','[]'):
            with self.assertRaises(HTTPError) as e:self.post('/api/simulate',payload)
            self.assertEqual(e.exception.code,400)
            self.assertIn('error',json.loads(e.exception.read()))

if __name__=='__main__':unittest.main()
