"""Send one daily publication report without an LLM or consuming bot updates."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

from scripts.check_publication import KST, ROOT, publication_health
from scripts.automation import render_fingerprint, state as deployment_state
from scripts.runtime_state import load, save

MARKER = 'telegram-notification.json'
REPOSITORY = 'ssy671/dogu-life-preview'


def send_message(token, chat_id, text):
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', token or ''):
        raise RuntimeError('Telegram bot token is missing or invalid')
    if not re.fullmatch(r'-?\d+', chat_id or ''):
        raise RuntimeError('Telegram chat ID must be the verified numeric destination')
    request = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=json.dumps({'chat_id': chat_id, 'text': text,
                         'link_preview_options': {'is_disabled': True}}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        if result.get('ok') is not True:
            raise ValueError('Telegram rejected the report')
    except Exception:
        # HTTP exceptions may contain the token-bearing URL; never print them.
        raise RuntimeError('Telegram delivery was not confirmed; automatic resend is disabled for this date') from None


def report(root, now, outcomes, run_id):
    try:
        health = publication_health(root, now)
    except (OSError, ValueError, KeyError, TypeError):
        health = {'ok': False, 'today_count': '확인 불가', 'remaining': '확인 불가',
                  'date': now.date().isoformat(), 'reason': 'publication_data_unreadable'}
    try:
        deployment = deployment_state(root)
        deployed = (deployment.get('status') == 'verified'
                    and deployment.get('fingerprint') == render_fingerprint(root))
    except (OSError, ValueError, KeyError, TypeError):
        deployed = False
    jobs_ok = (outcomes.get('publish') == 'success'
               and outcomes.get('verify') in ('success', 'skipped')
               and outcomes.get('checkpoint') in ('success', 'skipped'))
    healthy = health['ok'] and health['today_count'] == 3 and deployed and jobs_ok
    label = '✅ 도구생활 발행 정상' if healthy else '⚠️ 도구생활 발행 확인 필요'
    text = (f"{label} · {health['date']}\n"
            f"오늘 발행: {health['today_count']}편 / 목표 3편\n"
            f"배포 검증: {'정상' if deployed and jobs_ok else '확인 필요'}\n"
            f"대기 원고: {health['remaining']}편\n"
            f"확인 시각: {now:%H:%M} (한국 시간)")
    if not healthy:
        text += f"\n발행 검사: {health['reason']}\n작업 결과: " + ', '.join(
            f'{key}={outcomes.get(key, "unknown")}' for key in ('publish', 'verify', 'checkpoint'))
    if isinstance(health['remaining'], int) and health['remaining'] < 9:
        text += '\n원고 보충이 필요합니다.'
    text += f'\nhttps://github.com/{REPOSITORY}/actions/runs/{run_id}'
    return healthy, text


def deliver_once(root, now, outcomes, run_id, sender, persist):
    root = Path(root)
    now = now.astimezone(KST)
    if now.hour < 9:
        return 'before_publication_hour'
    path = root / 'content' / MARKER
    previous = json.loads(path.read_text()) if path.exists() else {}
    today = now.date().isoformat()
    if previous.get('date', '') >= today:
        return 'already_attempted_today'
    healthy, text = report(root, now, outcomes, run_id)
    if not healthy and (now.hour, now.minute) < (9, 23):
        return 'waiting_for_morning_retry'

    marker = {'date': today, 'status': 'reserved', 'updated_at': now.isoformat(), 'run_id': run_id}
    def record(status):
        marker['status'] = status
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(marker, indent=2) + '\n')
        temporary.replace(path)
        persist(root)

    # Save the reservation first. A timeout/crash must not send duplicate messages.
    record('reserved')
    try:
        sender(text)
    except Exception:
        record('uncertain')
        raise RuntimeError('Telegram delivery was not confirmed; inspect configuration before the next daily report') from None
    record('sent')
    return 'sent'


def main():
    token = os.environ.get('DOGU_TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('DOGU_TELEGRAM_CHAT_ID', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    if not token or not chat_id or not run_id.isdigit():
        print('::error::Configure DOGU_TELEGRAM_BOT_TOKEN and the verified DOGU_TELEGRAM_CHAT_ID before enabling reports.')
        return 1
    outcomes = {key: os.environ.get(f'PUBLICATION_{key.upper()}_RESULT', 'unknown')
                for key in ('publish', 'verify', 'checkpoint')}
    try:
        load()
        result = deliver_once(ROOT, datetime.now(timezone.utc), outcomes, run_id,
                              lambda text: send_message(token, chat_id, text), save)
    except Exception:
        print('::error::Daily Telegram report could not be completed. Check runtime state and bot configuration; no automatic resend is attempted for a reserved date.')
        return 1
    print('Daily Telegram report: ' + result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
