import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from .io import read_json

def write_new_output(path, data):
    published = False
    try:
        with TemporaryDirectory(prefix='.sweepforge-', dir=path.parent) as directory:
            staged = Path(directory) / 'output'
            with staged.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(staged, path)
            published = True
    except OSError as error:
        if not published:
            raise
        print(f'Output saved to {path}; could not remove staging directory {directory}: {error}',
              file=sys.stderr)


def main():
    parser=argparse.ArgumentParser(description='Timed-path linkage fitting and modeled full-cycle clearance')
    commands=parser.add_subparsers(dest='command',required=True)
    studio=commands.add_parser('studio',help='Open the local workshop')
    studio.add_argument('--port',type=int,default=6381)
    demo=commands.add_parser('examples',help='Write original synthetic requests and seed designs')
    demo.add_argument('--out',type=Path,required=True)
    for name in ['solve','check','export']:
        p=commands.add_parser(name)
        p.add_argument('input',type=Path)
        p.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='studio':
            from .server import serve
            serve(args.port)
            return 0
        if args.command=='examples':
            from .presets import examples
            value=examples()
            data=json.dumps(value,indent=2,allow_nan=False).encode()+b'\n'
        elif args.command=='export':
            from .exports import build_bundle
            data=build_bundle(read_json(args.input))
        else:
            from .core import analyze
            value=analyze(read_json(args.input),fit=args.command=='solve')
            data=json.dumps(value,indent=2,allow_nan=False).encode()+b'\n'
        write_new_output(args.out, data)
        print(str(args.out.resolve()))
        return 0
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as error:
        print(str(error),file=sys.stderr)
        return 2
