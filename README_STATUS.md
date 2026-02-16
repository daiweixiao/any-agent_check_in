# 快速查看状态

## 一键查看

### Windows
```cmd
status.bat
```

### Linux/Mac
```bash
./status.sh
```

或直接运行：
```bash
python quick_status.py
```

---

## 详细分析

### 查看详细状态
```bash
python check_status.py
```

### 分析失败原因
```bash
python analyze_failures.py
```

### 统计成功站点
```bash
python analyze_success.py
```

### 列出失败站点
```bash
python list_failed_sites.py
```

---

## 查看报告

### 完整分析报告（推荐）
```bash
cat AUTOMATION_REPORT.md
# 或 Windows
type AUTOMATION_REPORT.md
```

### 常见问题
```bash
cat FAQ.md
```

### 优化清单
```bash
cat IMPROVEMENT_CHECKLIST.md
```

### 总结文档
```bash
cat SUMMARY.md
```

---

## 运行签到

### 本地运行
```bash
python multi_site_checkin.py
```

### GitHub Actions
自动运行，每天北京时间 8:00

---

## 当前状态

- **自动化完成度**: 85%
- **当前成功率**: 53.9%
- **活跃站点**: 38 个
- **跳过站点**: 11 个

详见 `FAQ.md` 和 `AUTOMATION_REPORT.md`
