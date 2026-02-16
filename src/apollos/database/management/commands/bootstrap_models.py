import logging

from django.core.management.base import BaseCommand, CommandError

from apollos.utils.bootstrap import apply_bootstrap_config, load_bootstrap_config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Apply a bootstrap configuration file to create/update model providers, chat models, and server settings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            required=True,
            help="Path to the bootstrap JSON configuration file.",
        )

    def handle(self, *args, **options):
        config_path = options["config"]
        try:
            config = load_bootstrap_config(config_path)
        except (FileNotFoundError, ValueError) as e:
            raise CommandError(str(e)) from e

        try:
            apply_bootstrap_config(config)
            self.stdout.write(self.style.SUCCESS("Bootstrap configuration applied successfully."))
        except Exception as e:
            raise CommandError(f"Failed to apply bootstrap config: {e}") from e
