from celery import shared_task
from datetime import datetime

from api.mongodb import get_collection


@shared_task
def send_diffusion_alert(alert_data):
    alert_coll = get_collection('alerts')
    alert_coll.insert_one(alert_data)

    from alerts.wechat_alert import WeChatAlert
    from alerts.websocket_alert import WebSocketAlert

    WeChatAlert().send_alert(alert_data)
    WebSocketAlert().broadcast_alert(alert_data)


@shared_task
def send_anomaly_alert(alert_data):
    alert_coll = get_collection('alerts')
    doc = {
        'artifact_id': alert_data['artifact_id'],
        'alert_type': 'anomaly',
        'severity': 'critical',
        'message': f"检测到疑似仿古作伪，概率: {alert_data['forgery_probability']:.2%}",
        'data': {
            'forgery_probability': alert_data['forgery_probability'],
            'anomaly_score': alert_data['anomaly_score'],
        },
        'timestamp': datetime.now(),
        'status': 'active',
    }
    alert_coll.insert_one(doc)

    from alerts.wechat_alert import WeChatAlert
    from alerts.websocket_alert import WebSocketAlert

    WeChatAlert().send_alert(doc)
    WebSocketAlert().broadcast_alert(doc)
