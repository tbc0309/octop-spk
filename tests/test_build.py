import importlib.util
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class BuildTests(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','Linux Actions 执行真实 shell 升级测试')
    def test_upgrade_preserves_config_after_old_link_removed(self):
        for layout in ('docker','package/docker'):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)
                compose=directory/layout
                compose.mkdir(parents=True)
                (compose/'compose.yaml').write_text('{}')
                old=directory/'old-var'
                old.mkdir()
                content='OCTOP_ADMIN_USERNAME="original"\nOCTOP_DEFAULT_PASSWORD="Test12345"\n'
                (old/'container.env').write_text(content)
                script=directory/'prepare-compose'
                script.write_text((ROOT/'template/outer/scripts/prepare-compose').read_text().replace('/var/packages/docker-octop/var/container.env',str(directory/'missing.env')))
                env={k:v for k,v in os.environ.items() if not k.startswith('wizard_')}
                env.update(SYNOPKG_PKGINST_TEMP_DIR=str(directory),SYNOPKG_PKGVAR=str(old))
                subprocess.run(['sh',str(script),'--upgrade'],env=env,check=True,capture_output=True)
                (old/'container.env').unlink()
                subprocess.run(['sh',str(script)],env=env,check=True,capture_output=True)
                self.assertEqual((compose/'.octop-container.env').read_text(),content)
                self.assertEqual((compose/'.octop-container.env').stat().st_mode & 0o777,0o600)

    @unittest.skipIf(os.name=='nt','Linux Actions 执行真实 shell 升级测试')
    def test_reinstall_recovers_persistent_config_without_old_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            (directory/'package/docker').mkdir(parents=True)
            (directory/'package/docker/compose.yaml').write_text('{}')
            saved=directory/'volume1/@appdata/docker-octop/container.env'
            saved.parent.mkdir(parents=True)
            saved.write_text('OCTOP_DEFAULT_PASSWORD="Original123"\n')
            source=(ROOT/'template/outer/scripts/prepare-compose').read_text()
            source=source.replace('/var/packages/docker-octop/var/container.env',str(directory/'missing.env'))
            source=source.replace('/volume*/@appstore/docker-octop)',str(directory)+'/volume*/@appstore/docker-octop)')
            script=directory/'prepare-compose'
            script.write_text(source)
            env={k:v for k,v in os.environ.items() if not k.startswith(('wizard_','SYNOPKG_'))}
            env.update(SYNOPKG_PKGINST_TEMP_DIR=str(directory),SYNOPKG_PKGDEST=str(directory/'volume1/@appstore/docker-octop'))
            subprocess.run(['sh',str(script)],env=env,capture_output=True,check=True)
            self.assertEqual((directory/'package/docker/.octop-container.env').read_bytes(),saved.read_bytes())

    @unittest.skipIf(os.name=='nt','Linux Actions 执行真实 shell 升级测试')
    def test_missing_upgrade_config_fails_without_creating_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            (directory/'docker').mkdir()
            (directory/'docker/compose.yaml').write_text('{}')
            script=directory/'prepare-compose'
            script.write_text((ROOT/'template/outer/scripts/prepare-compose').read_text().replace('/var/packages/docker-octop/var/container.env',str(directory/'missing.env')))
            env={k:v for k,v in os.environ.items() if not k.startswith(('wizard_','SYNOPKG_'))}
            env['SYNOPKG_PKGINST_TEMP_DIR']=str(directory)
            result=subprocess.run(['sh',str(script),'--upgrade'],env=env,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((directory/'docker/.octop-container.env').exists())
    def test_version(self):
        self.assertEqual(builder.version_number('1.0.2b5'),'1.0.2-5')
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
            self.assertEqual(target.name,'docker-octop_v1.0.2-5_x86_64-DSM7.2.spk')
            with tarfile.open(target) as archive:
                info=archive.extractfile('INFO').read()
                self.assertIn(b'version="1.0.2-5"',info)
                self.assertIn(b'beta="no"',info)

    def test_wizard(self):
        for suffix in ('','_chs'):
            data=json.loads((ROOT/'template/outer/WIZARD_UIFILES'/('install_uifile'+suffix)).read_text(encoding='utf-8'))
            text=json.dumps(data)
            self.assertNotIn('storeArray',text)
            self.assertIn('wizard_log_level',text)

    def test_dsm_requirements(self):
        info=(ROOT/'template/outer/INFO').read_text(encoding='utf-8')
        self.assertIn('os_min_ver="7.2.1-69057"',info)
        script=(ROOT/'template/outer/scripts/start-stop-status').read_text(encoding='utf-8')
        self.assertIn('exit 3',script)
        self.assertIn('exit 4',script)

    def test_upgrade_wizard(self):
        for suffix,notice in (('', 'reinstall the browser and desktop environment'),('_chs','重新安装浏览器和桌面环境')):
            wizard=ROOT/'template/outer/WIZARD_UIFILES'/('upgrade_uifile'+suffix)
            data=json.loads(wizard.read_text(encoding='utf-8'))
            self.assertIn(notice,data[0]['items'][0]['desc'])
            self.assertNotIn('subitems',data[0]['items'][0])

if __name__=='__main__': unittest.main()
