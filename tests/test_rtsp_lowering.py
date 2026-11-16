"""Structural and machine-code evidence for the RTP byte path, not zero-copy I/O."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm
from tools.check_table_cost import function_body

ROOT=Path(__file__).resolve().parents[1]


class RtspLowering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=lower(load_program(ROOT/'examples/apps/liza_rtsp.liza', project_root=ROOT/'examples'))
        cls.functions={fn.name:fn for fn in cls.module}
        cls.text=llvm(cls.module)

    def test_no_parser_snapshots_or_loop_carried_event(self):
        step=self.functions['rtsp.tcp.step']
        operations=[op for block in step.blocks for op in block.operations]
        self.assertFalse([op for op in operations if op.op in ('storage.local','storage.read') and op.type=='rtsp.stream.State'])
        loop=self.functions['rtsp.tcp.buffered_event']
        operations=[op for block in loop.blocks for op in block.operations]
        self.assertFalse([op for op in operations if op.op=='phi' and op.type=='rtsp.tcp.Event'])
        self.assertFalse([op for op in operations if op.op=='storage.local'])
        feed=next(op for op in operations if op.op=='call' and op.callee=='rtsp.stream.feed')
        loan=next(op for op in operations if op.result==feed.args[0])
        self.assertEqual(loan.op,'loan.begin')
        projected=next(op for op in operations if op.result==loan.args[0])
        self.assertEqual((projected.op,projected.field_name),('storage.field','parser'))
        self.assertEqual(loan.owner_binding,projected.owner_binding)

    def test_payload_byte_and_wire_mutation_ir_do_not_copy(self):
        for name in ('rtsp.stream.frame_byte','httpws.bytes.put'):
            with self.subTest(name=name):
                body=function_body(self.text,name)
                self.assertNotRegex(body,r'alloca|memcpy|memmove')
                self.assertIn('store ',body)
        # The remaining header snapshot is deliberately cold: used once to
        # parse a completed RTSP header, never on an interleaved payload byte.
        feed=self.functions['rtsp.stream.feed']
        snapshots=[op.type for block in feed.blocks for op in block.operations if op.op=='storage.read' and op.type.startswith('[')]
        self.assertEqual(snapshots,['[u8;8192]'])

    @unittest.skipUnless(shutil.which('clang'),'Clang required')
    def test_payload_byte_machine_code_at_o0_o2_has_no_copy_calls(self):
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-codegen-') as folder:
            root=Path(folder);source=root/'client.ll';source.write_text(self.text)
            for opt in ('0','2'):
                target=root/('client'+opt+'.s')
                result=subprocess.run(['clang','-Wno-override-module','-O'+opt,'-S',str(source),'-o',str(target)],capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stderr)
                assembly=target.read_text()
                for name in ('rtsp.stream.frame_byte','httpws.bytes.put'):
                    start=re.search(r'^_?liza_'+re.escape(name)+r':',assembly,re.M)
                    self.assertIsNotNone(start,(opt,name))
                    tail=assembly[start.end():]
                    end=re.search(r'\.(?:cfi_endproc|seh_endproc)|^\.Lfunc_end|[;#]\s*-- End function',tail,re.M)
                    self.assertIsNotNone(end,(opt,name))
                    self.assertIsNone(re.search(r'memcpy|memmove',tail[:end.start()]),(opt,name))
