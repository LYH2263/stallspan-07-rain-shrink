# StallSpan 市集摊档开间

沿街段一维 First-Fit 开间分配，挡柱不可被摊位跨越，输出分配图与放不下清单。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4700 |
| API | http://localhost:9700 |
| API 文档 | http://localhost:9700/docs |
| Postgres | localhost:5448 |

健康检查：`GET http://localhost:9700/api/health`

## 使用说明

1. 在「集日」「街段」确认开市日与可用宽度。
2. 在「摊主」「挡柱」维护需求宽度与障碍位置。
3. 打开「分配带」执行一维开间分配。
4. 在「放不下」查看无法安置的摊位。

## 雨天缩宽

在「集日」可勾选雨天并填写宽度系数（0–1）。雨天时街段按 **登记宽度 × 系数** 作为唯一有效宽度：切空引擎、主图右端、放不下集合、运行抽屉共用同一宽度，无法再按晴天全长出图或出放不下。系数非法或雨天未填系数会被拒绝保存（400），各页保持改前值。

挡柱米标一旦超出缩后右端，**整根柱作废**，不参与切空、不在主图绘制；全系统只有这一种策略。

「分配带」右上的运行抽屉列出历史运行（天气、系数、登记→有效宽、放不下数），点选按当时快照渲染；旧运行右端不会被新系数回刷。配置改动后再次分配（或打开放不下页）会按新有效宽生成新运行，不吃改前缓存。

> 种子数据（周末夜市，雨天 0.8，东街段 30m → 有效 24m）只在空库写入；已有数据库卷升级需 `docker compose down -v` 重建卷。启动时会幂等补加 `market_days.rainy / width_coefficient` 列。

## 开发与测试

```bash
docker compose exec api pytest -q
```
