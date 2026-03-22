# 发布流程

这个仓库现在有了正式的版本和发布流程。

## 当前版本

项目的权威版本号保存在：

- `VERSION`
- `apps/web/package.json`

这两个位置必须保持一致。可以用下面的命令检查：

```bash
python3 scripts/verify-version.py
```

## Release 产物

每个 release 应该发布这些文件：

- `parallel-worlds-src-vX.Y.Z.tar.gz`
- `parallel-worlds-web-dist-vX.Y.Z.zip`
- `checksums.txt`

本地打包命令：

```bash
bash scripts/package-release.sh
```

或者指定版本号：

```bash
bash scripts/package-release.sh 0.1.0
```

## GitHub Release 流程

发布 workflow 在：

- `.github/workflows/release.yml`

它会在以下两种情况运行：

- 推送符合 `v*` 的 tag
- 手动触发 `workflow_dispatch`

workflow 会自动：

1. 检查版本文件是否一致
2. 跑 web build 和测试
3. 对 Python 代码做 compile 检查
4. 构建 release 压缩包
5. 上传产物
6. 从 `CHANGELOG.md` 里提取对应版本的 release notes
7. 发布 GitHub Release

## 推荐发布步骤

1. 更新 `CHANGELOG.md`
2. 更新 `VERSION`
3. 更新 `apps/web/package.json`
4. 运行：

```bash
python3 scripts/verify-version.py
cd apps/web && npm run build && npm run test
python3 -m compileall apps/api workers/story-generator
bash scripts/package-release.sh
```

5. 提交发布相关改动
6. 推送 commit
7. 推送 tag `vX.Y.Z`

## 这为什么重要

Release 会让项目更容易建立信任、更容易被引用，也更容易被传播。

对开源增长来说，一个持续发版本的仓库，会比“只有 commit、没有版本”的仓库更像一个真正活着的项目。
