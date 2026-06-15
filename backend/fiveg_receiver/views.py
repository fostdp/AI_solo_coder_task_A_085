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
        interval = request.data.get('interval', 30)
        simulator.start(interval=interval)
        return Response({'status': 'started', 'interval': interval})


class SimulatorStopView(APIView):
    def post(self, request):
        from .simulator import simulator
        simulator.stop()
        return Response({'status': 'stopped'})
