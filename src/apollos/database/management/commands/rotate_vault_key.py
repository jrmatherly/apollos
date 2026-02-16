"""Rotate the APOLLOS_VAULT_MASTER_KEY by re-encrypting all stored tokens."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.core.management.base import BaseCommand

from apollos.database.models import McpUserConnection
from apollos.utils.crypto import derive_key, encrypt_token


class Command(BaseCommand):
    help = "Rotate vault master key by re-encrypting all MCP OAuth tokens"

    def add_arguments(self, parser):
        parser.add_argument("--old-key", type=str, required=True, help="The previous APOLLOS_VAULT_MASTER_KEY value")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be rotated without changing data")

    def handle(self, *args, **options):
        old_key = options["old_key"]
        dry_run = options["dry_run"]

        if len(old_key) < 32:
            self.stderr.write(self.style.ERROR("Old key must be at least 32 characters"))
            return

        # Verify new key is set
        new_key = os.environ.get("APOLLOS_VAULT_MASTER_KEY", "")
        if not new_key or len(new_key) < 32:
            self.stderr.write(self.style.ERROR("APOLLOS_VAULT_MASTER_KEY must be set to the new key"))
            return

        if old_key == new_key:
            self.stderr.write(self.style.ERROR("Old and new keys are the same"))
            return

        connections = McpUserConnection.objects.exclude(access_token="").exclude(access_token__isnull=True)
        total = connections.count()
        self.stdout.write(f"Found {total} connections to re-encrypt")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes made"))
            return

        old_derived = derive_key(old_key, "mcp-token-encryption")
        success = 0
        errors = 0

        for conn in connections.iterator():
            try:
                # Decrypt with old key, re-encrypt with new key
                for field in ["access_token", "refresh_token"]:
                    value = getattr(conn, field)
                    if not value:
                        continue
                    data = base64.b64decode(value)
                    nonce, ct = data[:12], data[12:]
                    plaintext = AESGCM(old_derived).decrypt(nonce, ct, None).decode()
                    # Re-encrypt with new key (uses APOLLOS_VAULT_MASTER_KEY env var)
                    setattr(conn, field, encrypt_token(plaintext))

                conn.save(update_fields=["access_token", "refresh_token"])
                success += 1
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(f"Failed to rotate connection {conn.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Rotated {success}/{total} connections ({errors} errors)"))
