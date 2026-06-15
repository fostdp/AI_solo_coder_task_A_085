from django.apps import AppConfig


class AnomalyDetectorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'anomaly_detector'
    verbose_name = '异常检测'
