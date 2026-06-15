import signal
import time
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the 5G spectrum simulator as a standalone service'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=None, help='Upload interval in seconds (default: from settings or 21600)')
        parser.add_argument('--device-count', type=int, default=None, help='Number of spectrometer devices (default: 40)')
        parser.add_argument('--inject-forgery', type=str, nargs='*', help='Artifact IDs to inject forgery on startup')

    def handle(self, *args, **options):
        from fiveg_receiver.simulator import Receiver5GSimulator

        interval = options['interval'] or getattr(settings, 'SIMULATOR_INTERVAL', 21600)
        device_count = options['device_count'] or getattr(settings, 'SIMULATOR_DEVICE_COUNT', 40)
        band = getattr(settings, 'FIVE_G_BAND', 'n78')

        sim = Receiver5GSimulator(
            band=band,
            enable_network_sim=False,
            device_count=device_count,
            interval=interval,
        )

        if options['inject_forgery']:
            for artifact_id in options['inject_forgery']:
                forgery_type = 'chemical_staining'
                sim.inject_forgery(artifact_id, forgery_type)
                self.stdout.write(self.style.WARNING(f'Injected forgery: {artifact_id}'))

        shutdown = signal.signal(signal.SIGINT, signal.SIG_IGN)
        sim.start()

        self.stdout.write(
            self.style.SUCCESS(
                f'Simulator started: {device_count} devices, interval={interval}s ({interval/3600:.1f}h)'
            )
        )

        try:
            while sim.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Shutting down simulator...'))
            sim.stop()
