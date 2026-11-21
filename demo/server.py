"""Loopback-only HTTP interface for the interactive demo, never a repository file server."""
from dataclasses import asdict
from functools import lru_cache
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
from .bundle import load_bundle
from .runtime import AcceleratorConfig,simulate_matmul

WEB=Path(__file__).resolve().parent/'web'
DEFAULT_CONFIG={'lanes':8,'scratchpad_bytes':262144,'local_read_bytes_per_cycle':32,'external_bytes_per_cycle':32}

def configuration(raw):
    if not isinstance(raw,dict) or set(raw)-set(DEFAULT_CONFIG):raise ValueError('Choose valid hardware settings.')
    values=DEFAULT_CONFIG|raw
    for key,value in values.items():
        maximum={'lanes':32,'scratchpad_bytes':1048576,'local_read_bytes_per_cycle':128,'external_bytes_per_cycle':128}[key]
        if type(value) is not int or not 0<value<=maximum:raise ValueError(f'{key.replace("_"," ")} must be a positive integer up to {maximum:,}.')
    return AcceleratorConfig(**values)

def toy_run(data):
    if set(data)-{'preset','precision','config'}:raise ValueError('Unknown calculation setting.')
    preset=data.get('preset','single');precision=data.get('precision','int8')
    if preset=='single':left,right=[[2,3,1]],[[4],[5],[6]]
    elif preset=='parallel':left,right=[[2,3,1]],[[4]*8,[5]*8,[6]*8]
    elif preset=='tail':left,right=[[1]*64],[[1]*10 for _ in range(64)]
    else:raise ValueError('Choose one of the supplied examples.')
    config=configuration(data.get('config',{}))
    result=simulate_matmul(left,right,config,precision=precision)
    return {'preset':preset,'precision':precision,'config':asdict(config),'left':left,'right':right,'output':result.output,'metrics':result.metrics,'trace':result.trace}

@lru_cache(maxsize=1)
def bundle():return load_bundle()

def metadata():
    b=bundle();saved=b['metadata']
    return {'accuracy':saved['accuracy'],'quantization':saved['quantization'],'baseline':saved['baseline'],'examples':[e|{'pixels':b['pixels'][i].tolist()} for i,e in enumerate(saved['examples'])]}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):pass
    def send(self,status,payload,content_type='application/json; charset=utf-8'):
        body=json.dumps(payload,allow_nan=False).encode() if isinstance(payload,(dict,list)) else payload
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/meta':self.send(200,metadata());return
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/styles.css':('styles.css','text/css; charset=utf-8')}
        if path not in files:self.send(404,{'error':'Page not found.'});return
        filename,mime=files[path];self.send(200,(WEB/filename).read_bytes(),mime)
    def do_POST(self):
        if urlsplit(self.path).path!='/api/simulate':self.send(404,{'error':'Calculation not found.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16384:raise ValueError('The calculation request is too large or empty.')
            def reject(value):raise ValueError('Use finite numbers in the settings.')
            data=json.loads(self.rfile.read(size),parse_constant=reject)
            if not isinstance(data,dict):raise ValueError('Expected calculation settings.')
            self.send(200,toy_run(data))
        except (ValueError,TypeError,OverflowError) as error:self.send(400,{'error':str(error)})

def make_server(port=8000):
    bundle() # Fail early with an asset integrity error rather than a half-working page.
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
