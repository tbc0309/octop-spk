# Octop 群晖 Docker 套件

参考 TencentCloud/Octop 的 `fnos/docker`，适配群晖 DSM 7.2.1+ 和 Container Manager。当前为私有测试项目。

- 套件账户：`docker-octop`，`run-as: package`。
- 容器内部：`user: root`；不启用 privileged，不挂载 Docker socket 或 DSM 根目录。
- 网页端口：8088，由 Container Manager 注册，无重复的 port-config。
- 共享目录：`Octop`，挂载为 `/data`；卸载保留。
- Playwright 缓存：`/data/.cache/ms-playwright`，首次使用由应用下载浏览器。
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
