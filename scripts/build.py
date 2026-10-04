"""独立打包入口，只读取模板及官方 FPK，不依赖任何历史测试包。"""
import argparse
import hashlib
import io
import json
import re
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def version_number(version):
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?', version)
    if not match:
        raise ValueError('上游版本格式未支持，停止构建以避免误命名')
    major, minor, patch, stage, revision = match.groups()
    # 保留上游尾部编号作为套件修订号，不再使用测试阶段的偏移编号。
    build = int(revision or 1)
    return f'{major}.{minor}.{patch}-{build}'

def add(archive, name, data, stamp):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.uid = info.gid = 0
    info.uname = info.gname = 'root'
    info.mode = 0o755
    info.mtime = stamp
    archive.addfile(info, io.BytesIO(data))

def build(version, image, fpk, output):
    numeric = version_number(version)
    if not re.fullmatch(r'ghcr\.io/tencentcloud/octop@sha256:[0-9a-f]{64}', image):
        raise ValueError('必须使用固定的官方镜像摘要')
    stamp = int(time.time())
    outer = {p.relative_to(ROOT/'template/outer').as_posix():p.read_bytes() for p in (ROOT/'template/outer').rglob('*') if p.is_file() and p.name != 'package.tgz'}
    payload = {p.relative_to(ROOT/'template/payload').as_posix():p.read_bytes() for p in (ROOT/'template/payload').rglob('*') if p.is_file()}
    if any(name.endswith(('container.env','.env')) for name in payload):
        raise ValueError('模板中包含运行凭据，停止打包')
    with tarfile.open(fpk) as source:
        app = source.extractfile('app.tgz').read()
    with tarfile.open(fileobj=io.BytesIO(app)) as source:
        for size, name in ((64,'PACKAGE_ICON.PNG'),(256,'PACKAGE_ICON_256.PNG')):
            icon = source.extractfile(f'ui/images/icon_{size}.png').read()
            outer[name] = icon
            payload[f'app/images/octop-{size}.png'] = icon
    ui = json.loads(payload['app/config'])
    ui['.url']['SYNO.SDS.OctopDocker.Application']['title'] = 'Octop'
    payload['app/config'] = (json.dumps(ui,ensure_ascii=False,indent=2)+'\n').encode()
    compose = json.loads(payload['docker/compose.yaml'])
    compose['services']['octop']['image'] = image
    payload['docker/compose.yaml'] = (json.dumps(compose,indent=2)+'\n').encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:xz',preset=3) as archive:
        for name,data in sorted(payload.items()): add(archive,name,data,stamp)
    outer['package.tgz'] = buffer.getvalue()
    checksum = hashlib.md5(outer['package.tgz']).hexdigest()
    info = outer['INFO'].decode()
    changes = {'version':numeric,'beta':'no',
               'checksum':checksum,'changelog':f'更新 Octop 到 v{version}。升级会重建容器，请在 Web 控制台重新安装浏览器和桌面环境；共享数据保留。'}
    for key,value in changes.items():
        info = re.sub(rf'^{key}="[^"]*"',f'{key}="{value}"',info,flags=re.M)
    outer['INFO'] = (info.rstrip()+'\n').encode()
    output.mkdir(parents=True,exist_ok=True)
    target = output/f'docker-octop_v{numeric}_x86_64-DSM7.2.spk'
    temporary = target.with_suffix('.spk.tmp')
    with tarfile.open(temporary,'w') as archive:
        for name,data in sorted(outer.items()): add(archive,name,data,stamp)
    audit(temporary)
    temporary.replace(target)
    manifest = {'version':version,'dsm_version':numeric,'image':image,'source_fpk_sha256':hashlib.sha256(fpk.read_bytes()).hexdigest(),
                'spk_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'package_md5':checksum,'built_at':stamp}
    (output/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(target)
    return target

def audit(path):
    with tarfile.open(path) as archive:
        assert all(m.isfile() and m.mode==0o755 and m.uid==m.gid==0 for m in archive)
        info = archive.extractfile('INFO').read()
        assert info.endswith(b'\n') and not info.endswith(b'\n\n')
        payload = archive.extractfile('package.tgz').read()
        assert f'checksum="{hashlib.md5(payload).hexdigest()}"'.encode() in info
        assert json.loads(archive.extractfile('conf/privilege').read())['defaults']['run-as']=='package'
        assert 'port-config' not in json.loads(archive.extractfile('conf/resource').read())
        for lang in ('','_chs'):
            json.loads(archive.extractfile('WIZARD_UIFILES/install_uifile'+lang).read())
            json.loads(archive.extractfile('WIZARD_UIFILES/upgrade_uifile'+lang).read())
        with tarfile.open(fileobj=io.BytesIO(payload)) as inner:
            assert all(m.mode==0o755 and m.uid==m.gid==0 for m in inner)
            service = json.loads(inner.extractfile('docker/compose.yaml').read())['services']['octop']
            assert service['user']=='root' and not service.get('privileged')
            assert service['environment']['PLAYWRIGHT_BROWSERS_PATH']=='/data/.cache/ms-playwright'
            assert service['ports']==['8088:8088']

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',required=True)
    parser.add_argument('--image',required=True)
    parser.add_argument('--fpk',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    build(args.version,args.image,args.fpk,args.output)
