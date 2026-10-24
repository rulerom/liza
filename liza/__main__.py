import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
from .frontend import CompileError
from .modules import load_program
from .ir import lower, dump
from .backend import llvm
from .target import resolve as resolve_target
from .stdlib import link_flags


def main():
    parser = argparse.ArgumentParser(prog='liza', description='Experimental Liza compiler')
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('check', 'emit-ir', 'emit-llvm', 'build', 'run'):
        p = sub.add_parser(command)
        p.add_argument('source', type=Path)
        if command == 'run':
            p.epilog = 'Pass program arguments after --: liza run source.liza -- arg1 arg2'
        p.add_argument('--project-root', type=Path, help='explicit import root (default: entry source directory)')
        if command in ('emit-ir', 'emit-llvm', 'build'):
            p.add_argument('-o', '--output', type=Path)
        if command in ('emit-llvm', 'build', 'run'):
            p.add_argument('--clang', default='clang')
            p.add_argument('--target', help='Clang target triple (default: host)')
        if command in ('build', 'run'):
            p.add_argument('-O', choices=('0', '2'), default='2')
    arguments = sys.argv[1:]
    program_args = []
    separated = bool(arguments) and arguments[0] == 'run' and '--' in arguments
    if separated:
        split = arguments.index('--')
        arguments, program_args = arguments[:split], arguments[split+1:]
    args = parser.parse_args(arguments)
    try:
        program = load_program(args.source,args.project_root)
        inputs = set(program.source_paths)
        module = lower(program)
        if args.command == 'check':
            print(f'{args.source}: OK')
            return 0
        target = resolve_target(args.clang, args.target) if args.command != 'emit-ir' else None
        if args.command in ('emit-ir', 'emit-llvm'):
            text = dump(module) if args.command == 'emit-ir' else llvm(module, target)
            if args.output:
                if args.output.resolve() in inputs:
                    raise ValueError('output must not overwrite source')
                args.output.write_text(text, encoding='utf-8')
            else:
                print(text, end='')
            return 0
        with tempfile.TemporaryDirectory(prefix='liza-') as temporary:
            ir_file = Path(temporary) / 'module.ll'
            ir_file.write_text(llvm(module, target), encoding='utf-8')
            output = (args.output or Path('build') / args.source.stem).resolve() if args.command == 'build' else Path(temporary) / 'program'
            if output in inputs:
                raise ValueError('output must not overwrite source')
            if sys.platform == 'win32' and output.suffix.lower() != '.exe':
                output = Path(str(output)+'.exe')
            if output in inputs:
                raise ValueError('output must not overwrite source')
            output.parent.mkdir(parents=True, exist_ok=True)
            compiled = subprocess.run([args.clang, *target.flags, '-Werror=override-module', f'-O{args.O}', str(ir_file), *link_flags(module), '-o', str(output)])
            if compiled.returncode:
                return 1
            if args.command == 'build':
                print(output)
                return 0
            code = subprocess.run([str(output), *program_args]).returncode
            if sys.platform == 'win32':
                # Python's sys.exit uses a signed C long on Windows. Preserve
                # all 32 bits, including exception statuses and u32 main results.
                return code if code < 0x80000000 else code-(1 << 32)
            if code < 0:
                print(f'liza: program terminated by signal {-code}', file=sys.stderr)
                return 128 - code
            return code
    except CompileError as error:
        print(str(error) if error.source else f'{args.source}:{error}', file=sys.stderr)
        return 1
    except (OSError, ValueError, UnicodeError) as error:
        print(f'liza: {error}', file=sys.stderr)
        return 1
    except RecursionError:
        print('liza: source nesting exceeds prototype limit', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
