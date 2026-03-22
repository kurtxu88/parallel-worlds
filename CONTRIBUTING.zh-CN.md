# 贡献指南

感谢你一起来建设 Parallel Worlds。

## 开始之前

- 先读 [README.zh-CN.md](./README.zh-CN.md)
- 再读 [docs/roadmap.zh-CN.md](./docs/roadmap.zh-CN.md)
- 如果你的改动目标是增长、传播、演示效果或社区参与，也请读 [docs/growth-playbook.zh-CN.md](./docs/growth-playbook.zh-CN.md)
- 请只基于这个开源仓库里的技术栈做改动
- 请不要把托管认证、Supabase 默认依赖或私有 SaaS 流程重新带回 v1

## 环境准备

1. 把 `.env.example` 复制为 `.env`
2. 填写 `OPENAI_API_KEY`
3. 运行 `docker compose up --build`
4. 如果只做前端，可以用 `cd apps/web && npm install && npm run dev`

## 我们最欢迎的贡献

当前阶段最适合的贡献方向：

- 提升首次上手和本地运行成功率
- 提升 API、worker 和生成流程的稳定性
- 围绕创建 -> 生成 -> 游玩的闭环补测试
- 让创建、等待、分享、恢复流程更清晰
- 提升演示效果、README 表达和传播素材质量

## 开发预期

- 保持改动聚焦，便于 review
- 明确 API、状态和数据边界，不要依赖隐藏默认行为
- 不要提交密钥、真实生产地址或真实凭据
- 除非改动目标就是扩展认证能力，否则请保持 guest mode 行为
- 如果你加了新能力，也请同步更新相关文档

## 提交 Pull Request 时

- 说明你解决了什么问题
- 说明用户能感知到什么变化
- 如果改了 schema、环境变量或行为边界，请明确写出来
- 能补测试就尽量补测试
- 尽量让一个 PR 可以在一次 review 中看完

## 提交前检查

```bash
cd apps/web && npm install && npm run build && npm run test
python3 -m compileall apps/api workers/story-generator
```

## 作用域说明

公开版首发阶段暂不优先推进：

- 邀请机制
- 公开世界市场
- 托管认证流程

如果你想推动这些方向，建议先开 issue 对齐设计与取舍。

## 中文贡献者如何参与

你可以直接用中文：

- 提 issue
- 提 PR
- 写 world showcase
- 讨论产品方向或文档问题

我们会尽量保持关键贡献入口有中英文版本，降低参与门槛。

直接入口：

- 中文 Bug 模板：https://github.com/kurtxu88/parallel-worlds/issues/new?template=bug_report.zh-CN.yml
- 中文功能建议模板：https://github.com/kurtxu88/parallel-worlds/issues/new?template=feature_request.zh-CN.yml
- 中文世界展示模板：https://github.com/kurtxu88/parallel-worlds/issues/new?template=showcase.zh-CN.yml
