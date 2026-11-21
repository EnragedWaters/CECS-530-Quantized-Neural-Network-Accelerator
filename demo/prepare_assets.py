"""Build the small offline bundle from the published experiment, checking every result.

Run `python -m demo.prepare_assets` to reproduce the bundle using its FP32 weights.
Use --retrain to learn those weights again with notebook 05's original recipe.
The four checksum-verified MNIST archives are downloaded only if absent from
--cache. The live demo never downloads data or trains a model.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
import numpy as np
from . import runtime as core

ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path(__file__).resolve().parent/'assets'

def parameter_digest(model):
    digest=hashlib.sha256()
    for key in sorted(model):digest.update(key.encode());digest.update(model[key].tobytes())
    return digest.hexdigest()

def notebook_helpers():
    nb=json.loads((ROOT/'notebooks/05-int8-mnist-inference.ipynb').read_text())
    names={'decode_images','decode_labels','normalize_pixels','split_indices','train'}
    namespace={'np':np,'struct':__import__('struct'),'forward_fp32':core.forward_fp32}
    for cell in nb['cells']:
        if cell['cell_type']!='code':continue
        source=''.join(cell['source']).replace('%pip install matplotlib','')
        nodes=[node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name in names]
        if nodes:exec(compile(ast.Module(body=nodes,type_ignores=[]),'<published notebook helpers>','exec'),namespace)
    return namespace

def build(cache,fp32_path=None,retrain=False):
    saved=json.loads((ROOT/'results/mnist-results.json').read_text())
    timing=json.loads((ROOT/'results/accelerator-results.json').read_text())
    helpers=notebook_helpers();cache.mkdir(parents=True,exist_ok=True);raw={}
    for name,expected in saved['dataset_md5'].items():
        path=cache/name
        if not path.exists():
            print('Downloading',name,flush=True)
            with urllib.request.urlopen('https://ossci-datasets.s3.amazonaws.com/mnist/'+name,timeout=60) as response:payload=response.read()
            if hashlib.md5(payload).hexdigest()!=expected:raise ValueError('Dataset checksum mismatch: '+name)
            path.write_bytes(payload)
        payload=path.read_bytes()
        if hashlib.md5(payload).hexdigest()!=expected:raise ValueError('Dataset checksum mismatch: '+name)
        raw[name]=gzip.decompress(payload)
    pixels=helpers['decode_images'](raw['t10k-images-idx3-ubyte.gz'])
    labels=helpers['decode_labels'](raw['t10k-labels-idx1-ubyte.gz'])
    training=helpers['normalize_pixels'](helpers['decode_images'](raw['train-images-idx3-ubyte.gz']))
    indices=helpers['split_indices']()
    if retrain:
        train_labels=helpers['decode_labels'](raw['train-labels-idx1-ubyte.gz'])
        model,_=helpers['train'](training[indices['training']],train_labels[indices['training']],training[indices['validation']],train_labels[indices['validation']],**saved['training_settings'])
    else:
        with np.load(fp32_path or ASSETS/'network.npz',allow_pickle=False) as archive:
            model={k:archive[k if fp32_path else 'fp_'+k].copy() for k in ('w1','b1','w2','b2')}
    if parameter_digest(model)!=saved['fp32_parameter_sha256']:raise ValueError('FP32 model differs from the published experiment; do not replace the results.')
    settings=saved['quantization'];w1,s1=core.quantize_weight_matrix(model['w1']);w2,s2=core.quantize_weight_matrix(model['w2'])
    scale=core.calibrate_activation_scale(training[indices['calibration']],w1,model['b1'],input_scale=1/127,weight_scale=s1)
    if (s1,s2,scale)!=(settings['w1_scale'],settings['w2_scale'],settings['activation_scale']):raise ValueError('Calibration differs from the published experiment.')
    integer={'w1':w1,'w2':w2,'b1':core.quantize_bias_int32(model['b1'],(1/127)*s1),'b2':core.quantize_bias_int32(model['b2'],scale*s2),'multiplier':round((1/127)*s1/scale*2**30),'shift':30}
    if integer['multiplier']!=settings['multiplier']:raise ValueError('Integer multiplier differs from the published experiment.')
    values=helpers['normalize_pixels'](pixels);_,fp_scores=core.forward_fp32(values,model)
    ints=core.forward_integer_int8(core.quantize_int8(values,1/127),integer)
    fp_pred=fp_scores.argmax(axis=1);int_pred=ints['scores'].argmax(axis=1)
    for key,pred in [('fp32',fp_pred),('int8',int_pred)]:
        if hashlib.sha256(pred.astype(np.uint8).tobytes()).hexdigest()!=saved['prediction_sha256'][key]:raise ValueError(key+' predictions differ from the published experiment.')
    changed=np.flatnonzero(fp_pred!=int_pred)
    selected=np.array(sorted(set(range(16))|set(changed.tolist())),dtype=np.int32)
    ASSETS.mkdir(exist_ok=True)
    np.savez_compressed(ASSETS/'network.npz',**{'fp_'+k:v for k,v in model.items()},**{'int_'+k:integer[k] for k in ('w1','b1','w2','b2')})
    np.savez_compressed(ASSETS/'examples.npz',pixels=pixels[selected],labels=labels[selected],indices=selected)
    examples=[{'id':int(i),'label':int(labels[i]),'fp32_prediction':int(fp_pred[i]),'int8_prediction':int(int_pred[i]),'disagreement':bool(fp_pred[i]!=int_pred[i]),'verified_in_report':bool(i<16)} for i in selected]
    metadata={'schema_version':1,'source_notebook':'notebooks/05-int8-mnist-inference.ipynb','fp32_parameter_sha256':saved['fp32_parameter_sha256'],'training_settings':saved['training_settings'],'dataset_md5':saved['dataset_md5'],'quantization':settings,'accuracy':saved['accuracy'],'prediction_sha256':saved['prediction_sha256'],'baseline':timing,'examples':examples,'asset_sha256':{n:hashlib.sha256((ASSETS/n).read_bytes()).hexdigest() for n in ('network.npz','examples.npz')}}
    (ASSETS/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('Verified all 10,000 predictions; bundled',len(selected),'examples and the current calibrated model.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'notebooks/mnist-cache')
    parser.add_argument('--fp32-model',type=Path)
    parser.add_argument('--retrain',action='store_true')
    args=parser.parse_args();build(args.cache,args.fp32_model,args.retrain)
