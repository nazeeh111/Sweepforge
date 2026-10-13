import argparse
import json
import sys
from pathlib import Path
from .io import read_json

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
        # Refuse overwriting by default. Existing user artifacts remain intact.
        with args.out.open('xb') as stream:
            stream.write(data)
        print(str(args.out.resolve()))
        return 0
    except (ValueError,OSError,TypeError,KeyError,ArithmeticError) as error:
        print(str(error),file=sys.stderr)
        return 2
