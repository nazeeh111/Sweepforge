"""Fixed operations. Requests never select executable code or local paths."""
import base64
import sys
from .io import MAX_INPUT, decode, encoded

def main():
    try:
        job = decode(sys.stdin.buffer.read(MAX_INPUT + 1))
        action = job.get('action')
        from .core import analyze, validate_request
        if action == 'validate':
            result = {'request': validate_request(job['payload'])}
        elif action == 'solve':
            result = analyze(job['payload'], fit=True)
        elif action == 'check':
            result = analyze(job['payload'], fit=False)
        elif action == 'export':
            from .exports import build_bundle
            result = {'archive': base64.b64encode(build_bundle(job['payload'])).decode('ascii')}
        else:
            raise ValueError('Unsupported operation')
        sys.stdout.buffer.write(encoded({'ok':True,'result':result}))
        return 0
    except (ValueError, TypeError, KeyError, ArithmeticError) as error:
        sys.stdout.buffer.write(encoded({'ok':False,'error':str(error)}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
