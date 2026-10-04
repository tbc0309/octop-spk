# Octop 群晖 Docker 套件

参考 TencentCloud/Octop 的 `fnos/docker`，适配群晖 DSM 7.2.1+ 和 Container Manager。仓库保持私有，套件按正式版发布。

上游 1.0.2b5 对应套件正式版本 1.0.2-5，文件名使用套件版本；manifest 另行保留上游版本和镜像摘要。测试包 1.0.2-205 的版本号高于正式包，DSM 可能拒绝直接覆盖，需要保留数据后重新安装正式包。

- 套件账户：`docker-octop`，`run-as: package`。
- 容器内部：`user: root`；不启用 privileged，不挂载 Docker socket 或 DSM 根目录。
- 网页端口：8088，由 Container Manager 注册，无重复的 port-config。
- 共享目录：`Octop`，挂载为 `/data`；卸载保留。
- Playwright 缓存：`/data/.cache/ms-playwright`，首次使用由应用下载浏览器。
- browser / desktop Python 附加组件不等于 Chromium、浏览器系统库和完整 Linux 虚拟桌面已安装。网页提示按需安装不代表 SPK 丢失了镜像内容。
- 升级会重建容器，请在 Web 控制台重新安装浏览器和桌面环境；共享数据保留。浏览器文件可能仍在共享缓存，但容器内后装的系统运行库和桌面组件不会随共享数据保留。
- 中英文安装向导：账号、必填密码、日志级别、可选 OpenAI / DashScope API Key。
- 密钥只写入 0600 的运行时环境文件，不输出到日志。容器 root 可修改共享数据，不是宿主机权限隔离的绝对保证。

## 自动构建

工作流每 6 小时检测官方最新非草稿 Release（包括预发布），使用该版本的 Docker FPK 图标和官方镜像的实时摘要。镜像当前以 amd64 为目标。镜像摘要及源包 SHA256记录在 `build-manifest.json`，版本号本身不能证明镜像和 Release 版本相同。

新版本定时构建成功后创建私有 GitHub Release；手动构建默认只上传 artifact，勾选发布选项才发布。Release 是否为预发布跟随上游。

```sh
python scripts/build.py --version 1.0.2b5 --image ghcr.io/tencentcloud/octop@sha256:<digest> --fpk /path/to/Octop-fnos-docker-1.0.2b5.fpk
python -m unittest discover -s tests -v
```

依赖 Python 3.11+ 标准库，无硬编码 Windows 路径。所有归档项 root:root、0755、打包时间；INFO、向导和脚本通过自动检查。Actions 验证不代替 DSM 实体机安装与功能测试。

## 官方文档核对与已知限制

- [Docker Project Worker](https://help.synology.com/developer-guide/resource_acquisition/docker-project.html)：projects.path 指向包含 compose.yaml 的相对目录；Container Manager 1432 起提供。INFO 最低版本为 7.2.1-69057，与文档要求一致。
- [Data Share](https://help.synology.com/developer-guide/resource_acquisition/data_share.html)：通过 data-share 创建共享目录及访问权限，DSM 自动提供 shares 符号链接，卸载不删除共享数据。
- [Privilege Config](https://help.synology.com/developer-guide/privilege/privilege_config.html)：套件生命周期使用 package 身份；Compose 的容器 root 与宿主机套件身份是两回事。
- [控制脚本](https://help.synology.com/developer-guide/synology_package/scripts.html)：升级过程会执行新包 preinst/postinst。preupgrade 在旧包移除前将配置复制到新包解包目录；preinst 复用配置，不要求升级提供向导变量。失败后重装可从目标安装卷的 @appdata/docker-octop/container.env 恢复配置，不跨卷搜索、不重新生成密码。status 返回 0（运行）、3（未运行）或 4（查询失败、未知）。

### 2026-10-04 实体机只读诊断

192.168.9.164 的官方镜像摘要为 sha256:d04de8fe43fe9c64a9534b2521844fdeedb0aae6666b0ad53f6d26ca25d9f664，镜像标注版本 1.0.2b5。运行环境有 playwright、octop-browser、mss、pynput、pillow；没有 Xvnc、Openbox、XFCE。Chromium 已下载到共享缓存，但执行 --version 失败，ldd 检测到 24 个缺失库，包括 libglib-2.0、libatk、libnss3、libX11、libgbm 和 libasound。

官方 [镜像发布工作流](https://github.com/TencentCloud/Octop/blob/main/.github/workflows/docker-publish.yml) 实际使用 docker/Dockerfile，而非 fnos/docker/Dockerfile。两者都没有完整安装 Chromium 和虚拟桌面系统环境；[FnOS Dockerfile](https://github.com/TencentCloud/Octop/blob/main/fnos/docker/Dockerfile) 也明确将 Chromium 留给控制台按需下载。FPK manifest 的“预装附加组件”不能作为完整浏览器/桌面可直接运行的保证。

本次只修改说明和核对结果，不在 DSM 安装依赖、不重建容器、不更换官方镜像。运行时 apt 安装的系统依赖位于容器可写层，容器重建后通常需重新安装；要持久解决，应另行选择构建含系统依赖的派生镜像或实现可靠的容器初始化流程。
