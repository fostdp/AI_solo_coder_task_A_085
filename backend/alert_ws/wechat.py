import requests
import json
import logging
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class WeChatNotifier:

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or getattr(settings, 'WECHAT_WEBHOOK_URL', '')
        self.enabled = bool(self.webhook_url)

    def send_alert(self, alert_data: dict) -> bool:
        if not self.enabled:
            logger.warning("企业微信告警未配置，跳过发送")
            return False

        try:
            message = self._format_message(alert_data)

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": message
                }
            }

            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f"企业微信告警发送成功: {alert_data.get('artifact_id')}")
                return True
            else:
                logger.error(f"企业微信告警发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"企业微信告警发送异常: {e}")
            return False

    def _format_message(self, alert_data: dict) -> str:
        alert_type = alert_data.get('alert_type', 'unknown')
        severity = alert_data.get('severity', 'info')
        artifact_id = alert_data.get('artifact_id', '')
        message = alert_data.get('message', '')
        timestamp = alert_data.get('timestamp', datetime.now())

        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = str(timestamp)

        severity_emoji = {
            'critical': '🔴',
            'warning': '🟡',
            'info': '🟢'
        }.get(severity, '⚪')

        type_text = {
            'diffusion': '沁色深度超标',
            'anomaly': '疑似仿古作伪',
            'device': '设备异常'
        }.get(alert_type, '其他告警')

        msg_lines = [
            f"## {severity_emoji} 玉器监测告警",
            f"",
            f"**告警类型**: {type_text}",
            f"**玉器编号**: {artifact_id}",
            f"**告警级别**: {severity}",
            f"**告警时间**: {time_str}",
            f"",
            f"**告警详情**:",
            f"> {message}",
        ]

        if alert_data.get('data'):
            msg_lines.append("")
            msg_lines.append("**详细数据**:")
            for key, value in alert_data['data'].items():
                if isinstance(value, float):
                    msg_lines.append(f"- {key}: {value:.4f}")
                else:
                    msg_lines.append(f"- {key}: {value}")

        msg_lines.append("")
        msg_lines.append("请及时登录系统查看详细信息。")

        return "\n".join(msg_lines)

    def send_batch_alerts(self, alerts: list) -> dict:
        results = {'success': 0, 'failed': 0}
        for alert in alerts:
            if self.send_alert(alert):
                results['success'] += 1
            else:
                results['failed'] += 1
        return results
