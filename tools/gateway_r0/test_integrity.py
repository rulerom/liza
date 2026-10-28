"""Negative controls for published R0 evidence, without executing its binaries."""
import contextlib,hashlib,io,json,tarfile,tempfile,unittest
from pathlib import Path
from verify import verify

def sha(b):return hashlib.sha256(b).hexdigest()
def bundle(root,data=b'original',extra=False):
 with tarfile.open(root/'evidence.tar.gz','w:gz') as tar:
  for name,payload in [('report.json',data)]+([('unexpected',b'x')] if extra else []):
   m=tarfile.TarInfo(name);m.size=len(payload);tar.addfile(m,io.BytesIO(payload))
 (root/'report.json').write_bytes(b'original')
 (root/'manifest.json').write_text(json.dumps({'archive_sha256':sha((root/'evidence.tar.gz').read_bytes()),'files':{'report.json':sha(b'original')}}))
class Integrity(unittest.TestCase):
 def test_valid_then_changed_public_report(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bundle(root)
   with contextlib.redirect_stdout(io.StringIO()):verify(root)
   (root/'report.json').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'public report'):verify(root)
 def test_member_mutation_even_with_updated_archive_hash(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bundle(root,b'changed')
   with self.assertRaisesRegex(ValueError,'member hash'):verify(root)
 def test_unlisted_member(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);bundle(root,extra=True)
   with self.assertRaisesRegex(ValueError,'unexpected member'):verify(root)
if __name__=='__main__':unittest.main()
