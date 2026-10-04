"""获取官方发布包和镜像摘要，定时任务跳过已发布版本。"""
import hashlib
import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

def fetch(url, token=None, accept='application/json'):
    headers={'Accept':accept,'User-Agent':'octop-spk-builder'}
    if token: headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as response:
        return response.read(), response.headers

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--channel',choices=('stable','beta'),required=True)
    channel=parser.parse_args().channel
    token=os.environ['GITHUB_TOKEN']
    releases=json.loads(fetch('https://api.github.com/repos/TencentCloud/Octop/releases',token)[0])
    release=asset=None
    for candidate in releases:
        if candidate['draft']: continue
        for item in candidate['assets']:
            match=re.fullmatch(r'Octop-fnos-docker-(\d+\.\d+\.\d+(?:(a|b|rc)\d+)?)\.fpk',item['name'])
            if not match: continue
            is_beta=bool(match.group(2)) or candidate['prerelease']
            if is_beta != (channel=='beta'): continue
            release,asset=candidate,item
            break
        if release: break
    if release is None:
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output: output.write('build=false\n')
        print('该渠道暂无可构建的上游 Docker FPK')
        return
    version=asset['name'][len('Octop-fnos-docker-'):-4]
    from build import version_number
    version_number(version)
    tag='octop-v'+version
    existing=json.loads(fetch('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/releases',token)[0])
    build=not (os.environ.get('GITHUB_EVENT_NAME')=='schedule' and any(r['tag_name']==tag for r in existing))
    values={'build':str(build).lower(),'version':version,'tag':tag,'prerelease':str(channel=='beta').lower()}
    if build:
        registry_token=json.loads(fetch('https://ghcr.io/token?service=ghcr.io&scope=repository:tencentcloud/octop:pull')[0])['token']
        # 按发布版本取镜像，避免正式版渠道误用 latest 测试镜像。
        body,headers=fetch('https://ghcr.io/v2/tencentcloud/octop/manifests/'+version,registry_token,'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json')
        manifest=json.loads(body)
        if not any(m.get('platform',{}).get('architecture')=='amd64' for m in manifest.get('manifests',[])):
            raise RuntimeError('官方镜像未发现 amd64 平台，停止打包')
        digest=headers.get('Docker-Content-Digest') or 'sha256:'+hashlib.sha256(body).hexdigest()
        values['image']='ghcr.io/tencentcloud/octop@'+digest
        data=fetch(asset['browser_download_url'])[0]
        expected=asset.get('digest')
        if expected and expected!='sha256:'+hashlib.sha256(data).hexdigest(): raise RuntimeError('官方 FPK 下载校验失败')
        Path('build').mkdir(exist_ok=True)
        Path('build/source.fpk').write_bytes(data)
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output:
        for key,value in values.items(): output.write(f'{key}={value}\n')

if __name__=='__main__': main()
