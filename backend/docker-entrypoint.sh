#!/bin/bash
set -e

case "$1" in
    web)
        python manage.py collectstatic --noinput 2>/dev/null || true
        python manage.py migrate 2>/dev/null || true
        exec daphne -b 0.0.0.0 -p 8000 jade_monitor.asgi:application
        ;;
    celery-worker)
        shift
        QUEUE=${CELERY_QUEUE:-default}
        exec celery -A jade_monitor worker \
            --loglevel=info \
            --queues=$QUEUE \
            --concurrency=${CELERY_CONCURRENCY:-2} \
            --max-tasks-per-child=50 \
            --without-heartbeat
        ;;
    celery-beat)
        exec celery -A jade_monitor beat --loglevel=info
        ;;
    simulator)
        exec python manage.py run_simulator
        ;;
    *)
        exec "$@"
        ;;
esac
