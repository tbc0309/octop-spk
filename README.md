# Octop for Synology DSM

将 [TencentCloud/Octop](https://github.com/TencentCloud/Octop) 适配为群晖 SPK 套件，通过 Container Manager 部署官方 Docker 镜像。

Octop 是腾讯开源的多用户多智能体 AI 助手平台，支持 Web 控制台、CLI、IM 渠道与定时任务。本项目提供非官方群晖适配，不修改 Octop 应用源码。

## 环境要求

- DSM **7.2.1-69057 或更高版本**。
- x86_64 群晖设备；当前不提供 ARM 套件。
- 已安装 **Container Manager 20.10.23-1432 或更高版本**。
- 能访问 GitHub、GHCR 及应用组件所需的下载服务。
- 网页端口 **8088** 未被其他服务占用。

## 安装与使用

1. 从 [Releases](https://github.com/tbc0309/octop-spk/releases) 下载适合设备的 `.spk` 文件。
2. 在 DSM「套件中心 → 手动安装」中选择文件。
3. 设置管理员账号和密码。密码必填，须为 8–64 位并包含字母和数字，不允许常见弱密码。
4. 按需填写高级配置：日志级别默认 `info`（推荐），OpenAI API Key、DashScope API Key 可留空。
5. 完成安装并启动套件。首次安装需要下载官方容器镜像，请耐心等待。
6. 点击套件的「打开」，或访问 `http://NAS地址:8088`，在 Web 控制台配置 LLM 模型、IM 渠道及其他组件。

浏览器和桌面环境由 Octop Web 控制台按需安装。Python 附加组件与完整的 Chromium、系统运行库、虚拟桌面环境并非同一内容；附加组件已存在不代表浏览器或桌面已经可以运行。

## 升级与卸载

升级保留已保存的账号配置及共享数据，但会重新创建容器。

> **升级完成后，请在 Web 控制台重新安装浏览器和桌面环境。** 容器内后装的系统依赖不会随共享数据保留。中英文升级向导也会显示此提醒。

升级前建议备份 `Octop` 共享目录。卸载套件不会删除该共享目录；不再需要的数据可在卸载后通过 File Station 手动清理。

## 数据与权限

| 项目 | 说明 |
| --- | --- |
| 套件标识 | `docker-octop` |
| 套件账户 | `docker-octop`，生命周期脚本使用 `run-as: package` |
| 容器名称 | `synology-octop` |
| 共享目录 | `Octop`，挂载至容器的 `/data` |
| 应用数据 | 容器内 `/data/.octop` |
| 浏览器缓存 | 容器内 `/data/.cache/ms-playwright` |
| 运行配置 | 套件持久目录中的 `container.env`，权限 `0600` |

容器内部使用 `root`，不等于套件脚本以 DSM root 身份运行。项目不启用 privileged 模式，不挂载 Docker socket 或 DSM 根目录；容器仍可读写挂载的 `Octop` 共享目录，请妥善保护数据与密钥。

需要排查应用问题时，可在 Container Manager 中查看 `synology-octop` 的容器日志。提交日志前请删除密码、API Key 和其他敏感信息。

## 自动构建

GitHub Actions 每 6 小时分别检查正式版和测试版渠道，各自选择带有 Docker FPK 附件的最新上游非草稿 Release。发现尚未发布的版本后，自动构建并发布：正式版使用 beta="no"，发布为普通 Release 和 Latest；a/b/rc 版本使用 beta="yes"，发布为 Pre-release，不覆盖正式版 Latest。上游标记为预发布的版本也归入测试渠道。

也可在 **Actions → Octop 群晖 Docker 自动打包 → Run workflow** 手动构建：

- 默认只生成 Action artifact，不发布 Release。
- 可选择 all、stable 或 beta 渠道；勾选 `publish` 后发布构建附件，已有同名 Release 时更新该版本附件及发布状态。

构建时获取与上游版本同名的官方镜像标签并固定摘要，不使用 latest 混合两个渠道。对应镜像尚未发布时构建失败，不回退到其他版本的镜像。

发布附件包含 SPK 和 `build-manifest.json`。后者记录上游版本、套件版本、镜像摘要、源 FPK SHA256、SPK SHA256、payload checksum 及构建时间，便于核验与追踪。

套件文件名使用 DSM 套件版本，例如：

```text
docker-octop_v1.0.2-5_x86_64-DSM7.2.spk
```

文件名中的 `DSM7.2` 表示系统系列，实际最低版本以环境要求和套件 INFO 为准。

## 本地构建

需要 Python 3.11 或更高版本，打包程序仅依赖 Python 标准库。在 Linux 环境执行测试可同时验证升级配置恢复和 shell 脚本行为。

```sh
python -m unittest discover -s tests -v

python scripts/build.py \
  --version 1.0.2b5 \
  --image ghcr.io/tencentcloud/octop@sha256:<镜像摘要> \
  --fpk /path/to/Octop-fnos-docker-1.0.2b5.fpk
```

产物默认输出至 `dist/`。`--version` 使用上游版本，构建程序转换为 DSM 套件版本；例如 `1.0.2b5` 对应 `1.0.2-5`。

## 项目结构

```text
.github/workflows/build.yml  自动监测、构建和发布
scripts/prepare.py           获取上游 FPK 与官方镜像摘要
scripts/build.py             生成 SPK、校验产物和构建清单
template/outer/              INFO、生命周期脚本、资源配置和中英文向导
template/payload/            DSM 网页入口及 Docker Compose 配置
tests/                      打包、向导及升级配置恢复测试
```

## 相关项目与文档

- [Octop 官方项目](https://github.com/TencentCloud/Octop)：应用功能、模型配置与上游问题反馈。
- [本项目 Issues](https://github.com/tbc0309/octop-spk/issues)：群晖安装、升级和套件适配问题。
- [Synology Docker Project Worker](https://help.synology.com/developer-guide/resource_acquisition/docker-project.html)。
- [Synology Data Share](https://help.synology.com/developer-guide/resource_acquisition/data_share.html)。
- [Synology Privilege Config](https://help.synology.com/developer-guide/privilege/privilege_config.html)。
