import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class BuildTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(builder.version_number('1.0.2b5'),'1.0.2-205')
        with self.assertRaises(ValueError): builder.version_number('../bad')

    def test_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            app=io.BytesIO()
            with tarfile.open(fileobj=app,mode='w:gz') as archive:
                for size in (64,256):
                    builder.add(archive,f'ui/images/icon_{size}.png',(ROOT/'template/outer/PACKAGE_ICON.PNG').read_bytes(),1)
            fpk=directory/'source.fpk'
            with tarfile.open(fpk,'w') as archive: builder.add(archive,'app.tgz',app.getvalue(),1)
            target=builder.build('1.0.2b5','ghcr.io/tencentcloud/octop@sha256:'+'a'*64,fpk,directory/'out')
            builder.audit(target)

    def test_wizard(self):
        for suffix in ('','_chs'):
            data=json.loads((ROOT/'template/outer/WIZARD_UIFILES'/('install_uifile'+suffix)).read_text(encoding='utf-8'))
            text=json.dumps(data)
            self.assertNotIn('storeArray',text)
            self.assertIn('wizard_log_level',text)

if __name__=='__main__': unittest.main()
