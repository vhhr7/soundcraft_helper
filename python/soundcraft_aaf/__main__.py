import argparse
import json
import sys
from .reader import read_aaf


def main():
    p = argparse.ArgumentParser(description="Read AAF to a rational interchange plan; never modifies input")
    p.add_argument('aaf')
    p.add_argument('plan')
    p.add_argument('--composition', help='Explicit CompositionMob MobID when more than one exists')
    args = p.parse_args()
    try:
        plan = read_aaf(args.aaf, args.composition)
        with open(args.plan, 'x', encoding='utf-8') as out:
            json.dump(plan, out, ensure_ascii=False, indent=2)
        for warning in plan['warnings']:
            print(warning, file=sys.stderr)
    except Exception as e:
        print(json.dumps(dict(error=type(e).__name__, detail=str(e)), ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
