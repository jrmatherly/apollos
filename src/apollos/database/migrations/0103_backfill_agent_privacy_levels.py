from django.db import migrations


def convert_privacy_levels(apps, schema_editor):
    Agent = apps.get_model("database", "Agent")
    Agent.objects.filter(privacy_level="public").update(privacy_level="org")
    Agent.objects.filter(privacy_level="protected").update(privacy_level="team")


def reverse_privacy_levels(apps, schema_editor):
    Agent = apps.get_model("database", "Agent")
    Agent.objects.filter(privacy_level="org", managed_by_admin=True).update(privacy_level="public")
    Agent.objects.filter(privacy_level="team").update(privacy_level="protected")


class Migration(migrations.Migration):
    dependencies = [
        ("database", "0102_mcpserviceregistry_mcpuserconnection_agent_team_and_more"),
    ]

    operations = [
        migrations.RunPython(convert_privacy_levels, reverse_privacy_levels),
    ]
