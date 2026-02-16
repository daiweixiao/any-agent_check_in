#!/usr/bin/env python3
"""
快速查看自动化状态
Usage: python quick_status.py
"""
import json
from pathlib import Path

def main():
    # 读取数据
    info_file = Path('site_info.json')
    if not info_file.exists():
        print('❌ site_info.json 不存在，请先运行签到脚本')
        return

    info = json.load(open(info_file, 'r', encoding='utf-8'))
    summary = info.get('_meta', {}).get('summary', {})
    checkin_date = info.get('_meta', {}).get('checkin_date', '未运行')

    # 输出状态
    print('=' * 60)
    print('🤖 多站点自动签到系统 - 状态概览')
    print('=' * 60)
    print(f'\n📅 最后签到: {checkin_date}')
    print(f'\n📊 站点统计:')
    print(f'  总站点: {summary.get("total_sites", 0)}')
    print(f'  活跃站点: {summary.get("active_sites", 0)}')
    print(f'  跳过站点: {summary.get("skipped_sites", 0)}')
    print(f'  账号数: {summary.get("accounts", 0)}')

    total = summary.get('total_tasks', 0)
    success = summary.get('success', 0)
    already = summary.get('already_checked', 0)
    failed = summary.get('failed', 0)
    pending = summary.get('pending', 0)

    print(f'\n✅ 任务统计:')
    print(f'  总任务: {total}')
    print(f'  成功: {success}')
    print(f'  已签: {already}')
    print(f'  失败: {failed}')
    print(f'  待处理: {pending}')

    if total > 0:
        success_rate = (success + already) / total * 100
        print(f'\n📈 有效完成率: {success_rate:.1f}%')

        # 状态评级
        if success_rate >= 80:
            status = '🌟 优秀'
        elif success_rate >= 60:
            status = '✅ 良好'
        elif success_rate >= 40:
            status = '⚠️ 一般'
        else:
            status = '❌ 需要优化'

        print(f'   状态评级: {status}')

    # 快速建议
    print(f'\n💡 快速建议:')
    if failed > 20:
        print(f'  - 失败任务较多 ({failed}个)，建议查看 analyze_failures.py')
    if pending > 10:
        print(f'  - 待处理任务较多 ({pending}个)，建议重新运行签到')
    if success_rate < 60:
        print(f'  - 成功率偏低，建议查看 IMPROVEMENT_CHECKLIST.md')

    print(f'\n📚 详细报告:')
    print(f'  - AUTOMATION_REPORT.md - 完整分析报告')
    print(f'  - IMPROVEMENT_CHECKLIST.md - 优化清单')
    print(f'  - logs/checkin_*.log - 详细日志')

    print('\n' + '=' * 60)

if __name__ == '__main__':
    main()
