"""Load and validate the small, read-only bundle used by the offline demo."""
import hashlib
import json
from pathlib import Path
import numpy as np

ASSETS=Path(__file__).resolve().parent/'assets'

def load_bundle(directory=ASSETS):
    directory=Path(directory)
    metadata=json.loads((directory/'metadata.json').read_text())
    for name in ('network.npz','examples.npz'):
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=metadata['asset_sha256'][name]:
            raise ValueError('The demo asset changed: '+name)
    with np.load(directory/'network.npz',allow_pickle=False) as z:
        fp={k:z['fp_'+k].copy() for k in ('w1','b1','w2','b2')}
        integer={k:z['int_'+k].copy() for k in ('w1','b1','w2','b2')}
    expected={'w1':(784,64),'b1':(64,),'w2':(64,10),'b2':(10,)}
    digest=hashlib.sha256()
    for key in sorted(fp):
        if fp[key].shape!=expected[key] or fp[key].dtype!=np.float32 or not np.isfinite(fp[key]).all():raise ValueError('Invalid FP32 model array.')
        if integer[key].shape!=expected[key] or integer[key].dtype!=(np.int8 if key.startswith('w') else np.int32):raise ValueError('Invalid integer model array.')
        digest.update(key.encode());digest.update(fp[key].tobytes())
    if digest.hexdigest()!=metadata['fp32_parameter_sha256']:raise ValueError('FP32 parameter fingerprint changed.')
    integer.update(multiplier=metadata['quantization']['multiplier'],shift=metadata['quantization']['shift'])
    with np.load(directory/'examples.npz',allow_pickle=False) as z:pixels,labels,indices=(z[k].copy() for k in ('pixels','labels','indices'))
    if pixels.shape!=(len(indices),784) or pixels.dtype!=np.uint8 or labels.shape!=indices.shape or np.any(labels>9):raise ValueError('Invalid demo example arrays.')
    if indices.tolist()!=[e['id'] for e in metadata['examples']] or labels.tolist()!=[e['label'] for e in metadata['examples']]:raise ValueError('Example metadata does not match the bundled pixels.')
    for array in [*fp.values(),*[v for v in integer.values() if isinstance(v,np.ndarray)],pixels,labels,indices]:array.flags.writeable=False
    return {'metadata':metadata,'fp32':fp,'int8':integer,'pixels':pixels,'labels':labels,'indices':indices}
