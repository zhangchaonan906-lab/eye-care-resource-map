# P5 试点回滚与清理手册

## 运行前约束

- 每次导入需保存 `import_run_id`、source、region、`--limit` 和操作人，先运行 dry-run 并审核计数。
- 真实来源仅可在书面授权完成、来源评审为 `APPROVED` 且数据库 source 状态为 `approved` 后启用。命令必须显式提供 `PILOT_REAL_DATA=true`、地区和正整数 `--limit`。
- 本分支尚无真实 adapter；当前 P5-A 被阻塞，`pilot` 命令拒绝执行。不要为测试修改批准状态或直接写源表。

## 撤销流程

1. 暂停该来源后续任务并记录 `import_run_id`、source ID、region code、时间和原因。
2. 导出并安全保全该 run 的审计记录与下游候选清单；原始快照为审计证据，不可直接 DELETE 或覆盖 `source_records`。
3. 将该批次的候选/坐标 staging 状态置为 withdrawn/rejected 或由经审核的补偿迁移隔离；保留 source_record 外键、处理统计和审核事件。
4. 以 source + region + import_run 对账，确认没有 `facilities`、`facility_locations` 或发布视图写入。P5 禁止自动发布，因此任何发现均按安全事件处理并停止流程。
5. 保存执行人、时间、前后计数、SQL/迁移版本和复核人。不得对其他 source、region 或 run 做宽泛删除。
6. 确认修正原因和来源许可仍有效后，使用新的显式限量 run 重试；旧 run 不复用、不抹除。

目前未发生真实导入，因此没有待回滚的生产试点数据。
