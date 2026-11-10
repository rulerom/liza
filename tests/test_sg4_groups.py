"""SG4-B1 isolation, bounded native owners and language role enforcement."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
CONFIG='GroupConfig(65536,65536,1048576,1048576,65536,2,2,10000,3000)'

def compiler(*args):
    return subprocess.run([sys.executable,'-m','liza',*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=90)

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class MultipleGroups(unittest.TestCase):
    def test_native_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/('groups.exe' if sys.platform=='win32' else 'groups')
            platform='windows' if sys.platform=='win32' else 'posix'
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DLIZA_SG2_TESTING','-DLIZA_SG4_B1_TESTING','-I',str(ROOT/'liza/runtime'),
                 str(ROOT/'tests/native/sg4_groups.c'),str(ROOT/f'liza/runtime/net_{platform}.c'),
                 str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
            cmd+=['-lws2_32'] if sys.platform=='win32' else ['-pthread']
            def build(extra=()):
                p=subprocess.run(cmd+list(extra),capture_output=True,text=True,timeout=120)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            def run(case,*args,code=0):
                p=subprocess.run([str(exe),case,*map(str,args)],capture_output=True,text=True,timeout=30)
                self.assertEqual(p.returncode,code,p.stdout+p.stderr)
                return p
            build()
            for case in ('normal','fault','held','handback','reuse'):
                with self.subTest(case=case):run(case)
            for step in (1,2):run('pair_start',step)
            for step in range(1,25):
                with self.subTest(startup=step):run('startup',step)
            for case in ('foreign','stale','deadline'):
                with self.subTest(case=case):self.assertIn('process_abort no-cleanup',run(case,code=86).stdout)
            build(['-DSG2_BREAK_FOREIGN_RECEIPT'])
            for case in ('foreign','stale'):
                # The normal implementation rejects these receipts; the mutation accepts them.
                run(case,code=0)
            build(['-DSG2_BREAK_EARLY_RELEASE'])
            self.assertIn('release_rejected',run('deadline',code=86).stdout)
            build(['-DSG2_BREAK_EARLY_REUSE'])
            self.assertIn('logbook[gen].destroyed',run('handback',code=2).stderr)

    def test_language_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);exe=tmp/('pair.exe' if sys.platform=='win32' else 'pair')
            source=ROOT/'examples/workers/udp_groups.liza'
            for opt in ('0','2'):
                p=compiler('build',source,'-O',opt,'-o',exe);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                for _ in range(3):
                    p=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=compiler('emit-ir',source);self.assertEqual(p.returncode,0,p.stderr)
            contract=json.loads(p.stdout)['group_contract']
            self.assertEqual(len(contract['pair_entries']),4);self.assertEqual(contract['max_active_groups'],2)
            base=source.read_text()
            shared=tmp/'shared_pair.liza'
            shared.write_text(base.replace('return 17','return shared()+16').replace('return 18','return shared()+17')+'\nfn shared()->u32:pure {return 1}\n')
            p=compiler('check',shared);self.assertEqual(p.returncode,0,p.stderr)
            shared.write_text(base.replace('return 17','return shared()').replace('return exchange(24)','x=shared()\nreturn exchange(24)')+'\nfn shared()->u32:io {x=groups.send(1)\nreturn 17}\n')
            p=compiler('check',shared);self.assertNotEqual(p.returncode,0);self.assertIn('group role cannot',p.stderr)
            for old,new in [('return 17','x=groups.next()\nreturn 17'),('return exchange(23)','x=groups.send(2)\nreturn exchange(23)'),
                            ('pair=groups.run_pair(config,config)','x=producer_a()\npair=groups.run_pair(config,config)')]:
                bad=tmp/'bad.liza';bad.write_text(base.replace(old,new))
                p=compiler('check',bad);self.assertNotEqual(p.returncode,0,p.stdout)
                self.assertTrue('group role cannot' in p.stderr or 'callback cannot' in p.stderr,p.stderr)
