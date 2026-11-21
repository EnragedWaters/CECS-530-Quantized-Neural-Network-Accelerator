"""Loopback-only HTTP interface for the interactive demo, never a repository file server."""
from dataclasses import asdict
from functools import lru_cache
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import math
import numpy as np
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


def quantization_example(data):
    if set(data)-{'value','scale'}:raise ValueError('Unknown number setting.')
    value,scale=data.get('value',1.23),data.get('scale',.1)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (value,scale)) or not -1000<=value<=1000 or not .0001<=scale<=10:
        raise ValueError('Choose a value from -1,000 to 1,000 and a positive scale from 0.0001 to 10.')
    from .runtime import quantize_int8,quantize_bias_int32,requantize_relu_integer,checked_mac
    stored=int(quantize_int8([value],scale)[0]);reconstructed=stored*scale
    bias=int(quantize_bias_int32(np.array([.04]),.01)[0])
    hidden,_=requantize_relu_integer(np.array([20+bias],dtype=np.int32),1,2)
    return {'value':value,'scale':scale,'scaled':float(np.float32(value)/scale),'stored':stored,'reconstructed':reconstructed,'error':abs(value-reconstructed),'clipped':value/scale>127 or value/scale< -127,'large_product':checked_mac(0,127,127),'bias':bias,'biased_total':20+bias,'rescaled':int(hidden[0])}

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
        routes={'/api/simulate':toy_run,'/api/quantize':quantization_example}
        route=routes.get(urlsplit(self.path).path)
        if route is None:self.send(404,{'error':'Calculation not found.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16384:raise ValueError('The calculation request is too large or empty.')
            def reject(value):raise ValueError('Use finite numbers in the settings.')
            data=json.loads(self.rfile.read(size),parse_constant=reject)
            if not isinstance(data,dict):raise ValueError('Expected calculation settings.')
            self.send(200,route(data))
        except (ValueError,TypeError,OverflowError) as error:self.send(400,{'error':str(error)})

def make_server(port=8000):
    bundle() # Fail early with an asset integrity error rather than a half-working page.
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
