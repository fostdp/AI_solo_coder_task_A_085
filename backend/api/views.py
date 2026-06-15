from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import numpy as np
import json

from .mongodb import get_collection
from algorithms.diffusion_model import DiffusionModel
from algorithms.isolation_forest import AnomalyDetector
from alerts.wechat_alert import WeChatAlert
from alerts.websocket_alert import WebSocketAlert

diffusion_model = DiffusionModel()
anomaly_detector = AnomalyDetector()
wechat_alert = WeChatAlert()
ws_alert = WebSocketAlert()


class JadeArtifactList(APIView):
    def get(self, request):
        collection = get_collection('jade_artifacts')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        culture = request.GET.get('culture', '')
        keyword = request.GET.get('keyword', '')
        
        query = {}
        if culture:
            query['culture'] = culture
        if keyword:
            query['name'] = {'$regex': keyword}
        
        total = collection.count_documents(query)
        artifacts = list(collection.find(query).skip((page-1)*page_size).limit(page_size))
        
        for a in artifacts:
            a['_id'] = str(a['_id'])
        
        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'data': artifacts
        })


class JadeArtifactDetail(APIView):
    def get(self, request, artifact_id):
        collection = get_collection('jade_artifacts')
        artifact = collection.find_one({'artifact_id': artifact_id})
        if artifact:
            artifact['_id'] = str(artifact['_id'])
            return Response(artifact)
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class SpectrumDataView(APIView):
    def get(self, request, artifact_id):
        collection = get_collection('spectrum_data')
        limit = int(request.GET.get('limit', 100))
        start_time = request.GET.get('start_time', '')
        end_time = request.GET.get('end_time', '')
        
        query = {'artifact_id': artifact_id}
        if start_time:
            query['timestamp'] = {'$gte': datetime.fromisoformat(start_time)}
        if end_time:
            if 'timestamp' in query:
                query['timestamp']['$lte'] = datetime.fromisoformat(end_time)
            else:
                query['timestamp'] = {'$lte': datetime.fromisoformat(end_time)}
        
        data = list(collection.find(query).sort('timestamp', -1).limit(limit))
        for d in data:
            d['_id'] = str(d['_id'])
        
        return Response({'data': data})


class RamanSpectrumView(APIView):
    def get(self, request, artifact_id):
        collection = get_collection('raman_spectrum')
        latest = collection.find_one(
            {'artifact_id': artifact_id},
            sort=[('timestamp', -1)]
        )
        if latest:
            latest['_id'] = str(latest['_id'])
            return Response(latest)
        return Response({'error': 'No data'}, status=status.HTTP_404_NOT_FOUND)


class XRFSpectrumView(APIView):
    def get(self, request, artifact_id):
        collection = get_collection('xrf_spectrum')
        latest = collection.find_one(
            {'artifact_id': artifact_id},
            sort=[('timestamp', -1)]
        )
        if latest:
            latest['_id'] = str(latest['_id'])
            return Response(latest)
        return Response({'error': 'No data'}, status=status.HTTP_404_NOT_FOUND)


class DiffusionResultView(APIView):
    def get(self, request, artifact_id):
        collection = get_collection('diffusion_results')
        limit = int(request.GET.get('limit', 10))
        data = list(collection.find(
            {'artifact_id': artifact_id}
        ).sort('timestamp', -1).limit(limit))
        
        for d in data:
            d['_id'] = str(d['_id'])
        
        return Response({'data': data})
    
    def post(self, request, artifact_id):
        collection = get_collection('diffusion_results')
        artifact_coll = get_collection('jade_artifacts')
        
        artifact = artifact_coll.find_one({'artifact_id': artifact_id})
        if not artifact:
            return Response({'error': 'Artifact not found'}, status=404)
        
        thickness = artifact.get('size', {}).get('thickness', 2.0)
        temperature = request.data.get('temperature', 25)
        humidity = request.data.get('humidity', 50)
        time_hours = request.data.get('time_hours', 1000)
        
        fe_result = diffusion_model.simulate_diffusion(
            ion_type='Fe3+',
            thickness_mm=thickness,
            time_hours=time_hours,
            temperature=temperature,
            humidity=humidity
        )
        
        mn_result = diffusion_model.simulate_diffusion(
            ion_type='Mn2+',
            thickness_mm=thickness,
            time_hours=time_hours,
            temperature=temperature,
            humidity=humidity
        )
        
        penetration_depth_fe = diffusion_model.calculate_penetration_depth(fe_result['concentration_profile'], thickness)
        penetration_depth_mn = diffusion_model.calculate_penetration_depth(mn_result['concentration_profile'], thickness)
        
        result = {
            'artifact_id': artifact_id,
            'timestamp': datetime.now(),
            'fe3_diffusion': fe_result,
            'mn2_diffusion': mn_result,
            'penetration_depth_fe_mm': penetration_depth_fe,
            'penetration_depth_mn_mm': penetration_depth_mn,
            'max_penetration_mm': max(penetration_depth_fe, penetration_depth_mn),
            'temperature': temperature,
            'humidity': humidity,
            'simulation_time_hours': time_hours
        }
        
        collection.insert_one(result)
        result['_id'] = str(result['_id'])
        
        from django.conf import settings
        if result['max_penetration_mm'] > settings.DIFFUSION_ALERT_THRESHOLD_MM:
            alert_data = {
                'artifact_id': artifact_id,
                'alert_type': 'diffusion',
                'severity': 'warning',
                'message': f'沁色深度超过阈值: {result["max_penetration_mm"]:.2f}mm',
                'data': {'penetration_mm': result['max_penetration_mm']},
                'timestamp': datetime.now(),
                'status': 'active'
            }
            get_collection('alerts').insert_one(alert_data)
            wechat_alert.send_alert(alert_data)
            ws_alert.broadcast_alert(alert_data)
        
        return Response(result)


class AnomalyResultView(APIView):
    def get(self, request, artifact_id):
        collection = get_collection('anomaly_results')
        limit = int(request.GET.get('limit', 10))
        data = list(collection.find(
            {'artifact_id': artifact_id}
        ).sort('timestamp', -1).limit(limit))
        
        for d in data:
            d['_id'] = str(d['_id'])
        
        return Response({'data': data})
    
    def post(self, request, artifact_id):
        collection = get_collection('anomaly_results')
        xrf_coll = get_collection('xrf_spectrum')
        raman_coll = get_collection('raman_spectrum')
        
        xrf_data = xrf_coll.find_one(
            {'artifact_id': artifact_id},
            sort=[('timestamp', -1)]
        )
        raman_data = raman_coll.find_one(
            {'artifact_id': artifact_id},
            sort=[('timestamp', -1)]
        )
        
        if not xrf_data and not raman_data:
            return Response({'error': 'No spectrum data'}, status=400)
        
        features = anomaly_detector.extract_features(xrf_data, raman_data)
        result = anomaly_detector.detect(features, artifact_id)
        
        result_doc = {
            'artifact_id': artifact_id,
            'timestamp': datetime.now(),
            'anomaly_score': result['anomaly_score'],
            'is_anomaly': result['is_anomaly'],
            'forgery_probability': result['forgery_probability'],
            'features': result['features'],
            'anomaly_reasons': result['anomaly_reasons']
        }
        
        collection.insert_one(result_doc)
        result_doc['_id'] = str(result_doc['_id'])
        
        from django.conf import settings
        if result['forgery_probability'] > settings.ANOMALY_SCORE_THRESHOLD:
            alert_data = {
                'artifact_id': artifact_id,
                'alert_type': 'anomaly',
                'severity': 'critical',
                'message': f'检测到疑似仿古作伪，概率: {result["forgery_probability"]:.2%}',
                'data': {
                    'forgery_probability': result['forgery_probability'],
                    'anomaly_score': result['anomaly_score']
                },
                'timestamp': datetime.now(),
                'status': 'active'
            }
            get_collection('alerts').insert_one(alert_data)
            wechat_alert.send_alert(alert_data)
            ws_alert.broadcast_alert(alert_data)
        
        return Response(result_doc)


class DensityMapView(APIView):
    def get(self, request, artifact_id):
        diffusion_coll = get_collection('diffusion_results')
        artifact_coll = get_collection('jade_artifacts')
        
        diffusion = diffusion_coll.find_one(
            {'artifact_id': artifact_id},
            sort=[('timestamp', -1)]
        )
        artifact = artifact_coll.find_one({'artifact_id': artifact_id})
        
        if not diffusion or not artifact:
            return Response({'error': 'No data'}, status=404)
        
        width = artifact.get('size', {}).get('width', 50)
        height = artifact.get('size', {}).get('length', 80)
        
        fe_profile = np.array(diffusion['fe3_diffusion']['concentration_profile'])
        mn_profile = np.array(diffusion['mn2_diffusion']['concentration_profile'])
        
        grid_size = 100
        density_map = np.zeros((grid_size, grid_size))
        
        center_x = grid_size // 2
        center_y = grid_size // 2
        
        for i in range(grid_size):
            for j in range(grid_size):
                dist_from_edge = min(i, j, grid_size-1-i, grid_size-1-j)
                normalized_dist = dist_from_edge / (grid_size / 2)
                
                if normalized_dist < len(fe_profile) / grid_size:
                    idx = int(normalized_dist * grid_size)
                    if idx < len(fe_profile) and idx < len(mn_profile):
                        density_map[i, j] = fe_profile[min(idx, len(fe_profile)-1)] * 0.6 + \
                                            mn_profile[min(idx, len(mn_profile)-1)] * 0.4
        
        max_val = density_map.max() if density_map.max() > 0 else 1
        density_map_normalized = (density_map / max_val * 255).astype(int)
        
        return Response({
            'artifact_id': artifact_id,
            'grid_size': grid_size,
            'density_map': density_map_normalized.tolist(),
            'max_concentration': float(max_val),
            'width_mm': width,
            'height_mm': height
        })


class AlertList(APIView):
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


class AlertAcknowledge(APIView):
    def post(self, request, alert_id):
        collection = get_collection('alerts')
        from bson import ObjectId
        
        result = collection.update_one(
            {'_id': ObjectId(alert_id)},
            {'$set': {'status': 'acknowledged', 'acknowledged_at': datetime.now()}}
        )
        
        if result.modified_count > 0:
            return Response({'success': True})
        return Response({'error': 'Alert not found'}, status=404)


class DeviceList(APIView):
    def get(self, request):
        collection = get_collection('devices')
        device_type = request.GET.get('type', '')
        
        query = {}
        if device_type:
            query['device_type'] = device_type
        
        devices = list(collection.find(query))
        for d in devices:
            d['_id'] = str(d['_id'])
        
        return Response({'data': devices, 'total': len(devices)})


class SpectrumUpload(APIView):
    def post(self, request):
        data = request.data
        artifact_id = data.get('artifact_id')
        device_id = data.get('device_id')
        spectrum_type = data.get('type', 'raman')
        spectrum_data = data.get('spectrum_data', [])
        
        if not artifact_id or not spectrum_data:
            return Response({'error': 'Missing required fields'}, status=400)
        
        timestamp = datetime.now()
        
        if spectrum_type == 'raman':
            collection = get_collection('raman_spectrum')
        else:
            collection = get_collection('xrf_spectrum')
        
        doc = {
            'artifact_id': artifact_id,
            'device_id': device_id,
            'timestamp': timestamp,
            'spectrum_data': spectrum_data,
            'wavelengths': data.get('wavelengths', [])
        }
        
        collection.insert_one(doc)
        doc['_id'] = str(doc['_id'])
        
        spectrum_coll = get_collection('spectrum_data')
        spectrum_coll.insert_one({
            'artifact_id': artifact_id,
            'device_id': device_id,
            'type': spectrum_type,
            'timestamp': timestamp
        })
        
        return Response({'success': True, 'data': doc})


class StatsSummary(APIView):
    def get(self, request):
        artifact_coll = get_collection('jade_artifacts')
        alert_coll = get_collection('alerts')
        device_coll = get_collection('devices')
        anomaly_coll = get_collection('anomaly_results')
        
        total_artifacts = artifact_coll.count_documents({})
        hongshan_count = artifact_coll.count_documents({'culture': '红山文化'})
        liangzhu_count = artifact_coll.count_documents({'culture': '良渚文化'})
        
        active_alerts = alert_coll.count_documents({'status': 'active'})
        total_alerts = alert_coll.count_documents({})
        
        devices_online = device_coll.count_documents({'status': 'online'})
        total_devices = device_coll.count_documents({})
        
        anomalies = list(anomaly_coll.find({}).sort('timestamp', -1).limit(200))
        high_risk = sum(1 for a in anomalies if a.get('forgery_probability', 0) > 0.7)
        
        return Response({
            'total_artifacts': total_artifacts,
            'hongshan_count': hongshan_count,
            'liangzhu_count': liangzhu_count,
            'active_alerts': active_alerts,
            'total_alerts': total_alerts,
            'devices_online': devices_online,
            'total_devices': total_devices,
            'high_risk_artifacts': high_risk,
            'last_update': datetime.now().isoformat()
        })


class SimulatorStart(APIView):
    def post(self, request):
        from simulator.jade_simulator import simulator
        interval = request.data.get('interval', 30)
        simulator.start(interval=interval)
        return Response({'status': 'started', 'interval': interval})


class SimulatorStop(APIView):
    def post(self, request):
        from simulator.jade_simulator import simulator
        simulator.stop()
        return Response({'status': 'stopped'})
