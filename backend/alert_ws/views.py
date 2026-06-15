from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from api.mongodb import get_collection


class AlertListView(APIView):
    def get(self, request):
        collection = get_collection('alerts')
        status_filter = request.GET.get('status', '')
        alert_type = request.GET.get('type', '')
        limit = int(request.GET.get('limit', 50))

        query = {}
        if status_filter:
            query['status'] = status_filter
        if alert_type:
            query['alert_type'] = alert_type

        alerts = list(collection.find(query).sort('timestamp', -1).limit(limit))
        for a in alerts:
            a['_id'] = str(a['_id'])

        return Response({'data': alerts, 'total': len(alerts)})


class AlertAcknowledgeView(APIView):
    def post(self, request, alert_id):
        collection = get_collection('alerts')
        from bson import ObjectId

        result = collection.update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {'status': 'acknowledged', 'acknowledged_at': datetime.now()}}
        )

        if result.modified_count > 0:
            return Response({'success': True})
        return Response({'error': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)
