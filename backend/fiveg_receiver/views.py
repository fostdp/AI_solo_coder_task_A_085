from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .tasks import receive_spectrum


class SpectrumUploadView(APIView):
    def post(self, request):
        data = request.data
        artifact_id = data.get('artifact_id')
        device_id = data.get('device_id')
        spectrum_type = data.get('type', 'raman')
        spectrum_data = data.get('spectrum_data', [])
        wavelengths = data.get('wavelengths', [])
        energies = data.get('energies', [])

        if not artifact_id or not spectrum_data:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        receive_spectrum.delay(
            artifact_id=artifact_id,
            device_id=device_id,
            spectrum_type=spectrum_type,
            spectrum_data=spectrum_data,
            wavelengths=wavelengths,
            energies=energies,
        )

        return Response({'status': 'submitted', 'artifact_id': artifact_id})


class SimulatorStartView(APIView):
    def post(self, request):
        from .simulator import simulator
        interval = request.data.get('interval')
        simulator.start(interval=interval)
        return Response({
            'status': 'started',
            'interval': simulator.interval,
            'device_count': len(simulator.raman_devices) + len(simulator.xrf_devices),
        })


class SimulatorStopView(APIView):
    def post(self, request):
        from .simulator import simulator
        simulator.stop()
        return Response({'status': 'stopped'})


class ForgeryInjectView(APIView):
    def post(self, request):
        from .simulator import simulator
        artifact_id = request.data.get('artifact_id')
        forgery_type = request.data.get('forgery_type', 'chemical_staining')
        if not artifact_id:
            return Response({'error': 'artifact_id required'}, status=status.HTTP_400_BAD_REQUEST)
        success = simulator.inject_forgery(artifact_id, forgery_type)
        if success:
            return Response({'status': 'injected', 'artifact_id': artifact_id, 'forgery_type': forgery_type})
        return Response({'error': 'Invalid forgery_type'}, status=status.HTTP_400_BAD_REQUEST)


class ForgeryRemoveView(APIView):
    def post(self, request):
        from .simulator import simulator
        artifact_id = request.data.get('artifact_id')
        if not artifact_id:
            return Response({'error': 'artifact_id required'}, status=status.HTTP_400_BAD_REQUEST)
        removed = simulator.remove_forgery(artifact_id)
        return Response({'status': 'removed' if removed else 'not_found', 'artifact_id': artifact_id})


class ForgeryListView(APIView):
    def get(self, request):
        from .simulator import simulator
        injections = simulator.get_forgery_injections()
        return Response({
            'count': len(injections),
            'injections': {k: {'type': v['type'], 'description': v['description'], 'injected_at': v['injected_at']} for k, v in injections.items()},
        })
