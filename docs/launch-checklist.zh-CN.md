# 发布清单

每次要做比较重要的公开曝光时，比如发 Hacker News、X、Reddit、博客文章或 release 公告，都可以先过一遍这份清单。

## 发布前

- 用干净环境确认 `docker compose up --build` 能跑通
- 确认 `npm run build`、`npm run test`、`python3 -m compileall apps/api workers/story-generator` 全部通过
- 确认 README 与当前产品状态、截图和文案一致
- 确认 starter seeds 仍然能稳定产出有意思的结果
- 确认社交预览图和站点元信息仍符合当前定位
- 在发帖前先把 release note 草稿写出来

## 发布当天要准备的素材

- 一段面向普通用户的简短介绍
- 一段面向开发者的简短介绍
- 一张截图或一段短视频
- 一个稳定可复现的 starter seed 链接
- 一个直接通往 roadmap 或贡献指南的链接

## 发布当天要做的动作

- 用一个明确的 hook 发出公告
- 在最开始几个小时里保持在线，及时回复 issue
- 实时记录大家重复提到的困惑点
- 当天就把高频问题转成 README 或文档改进

## 发布后

- 记录流量和讨论来自哪里
- 记录哪一个 demo seed 或切入角度表现最好
- 快速跟进每一个外部 issue 或 showcase
- 总结这次学到的内容，并转成下一次真实发布的改动
