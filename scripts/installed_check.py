"""Run CLI and portable source from an unrelated working directory."""
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

def main():
    env=dict(os.environ)
    env.pop('PYTHONPATH',None)
    with tempfile.TemporaryDirectory(prefix='sweepforge-installed-') as directory:
        root=Path(directory)
        def run(*args):
            return subprocess.run([sys.executable,*args],cwd=root,env=env,check=True,text=True,capture_output=True)
        run('-m','sweepforge','examples','--out','examples.json')
        examples=json.loads((root/'examples.json').read_text())
        receipts=[]
        for i, example in enumerate(examples):
            payload={'request':example['request'],'design':example['design']}
            (root/f'input-{i}.json').write_text(json.dumps(payload))
            run('-m','sweepforge','check',f'input-{i}.json','--out',f'check-{i}.json')
            checked=json.loads((root/f'check-{i}.json').read_text())
            expected=['clear_under_model','collision','clear_under_model'][i]
            assert checked['report']['state']==expected,(i,checked['report'])
            receipts.append({'example':example['name'],'state':expected,'hash':checked['report']['inputSha256']})
        (root/'target.json').write_text(json.dumps(examples[0]['request']))
        run('-m','sweepforge','solve','target.json','--out','solved.json')
        solved=json.loads((root/'solved.json').read_text())
        assert solved['fit']['maxErrorMm']<1e-6,solved['fit']
        run('-m','sweepforge','export','input-0.json','--out','bundle.zip')
        extracted=root/'portable';extracted.mkdir()
        with zipfile.ZipFile(root/'bundle.zip') as archive:
            for name in archive.namelist():
                assert not name.startswith('/') and '..' not in Path(name).parts
            archive.extractall(extracted)
        outside=root/'unrelated';outside.mkdir()
        replay=subprocess.run([sys.executable,str(extracted/'verifier.py')],cwd=outside,env=env,check=True,text=True,capture_output=True)
        recomputed=json.loads(replay.stdout)
        assert recomputed['report']['state']=='clear_under_model'
        print(json.dumps({'installedExamples':receipts,'inverseMaxErrorMm':solved['fit']['maxErrorMm'],'portableRecomputation':{'state':recomputed['report']['state'],'inputSha256':recomputed['report']['inputSha256'],'baseline':recomputed.get('baseline')}},indent=2))

if __name__=='__main__':
    main()
