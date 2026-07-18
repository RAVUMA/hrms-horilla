from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeAuthSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password_rotation_enabled", models.BooleanField(default=False)),
                ("rotation_interval_seconds", models.PositiveIntegerField(default=300)),
                ("rotation_started_at", models.DateTimeField(blank=True, null=True)),
                ("last_rotation_at", models.DateTimeField(blank=True, null=True)),
                ("emergency_mode_enabled", models.BooleanField(default=False)),
                ("emergency_password_hash", models.CharField(blank=True, max_length=128)),
                ("emergency_password_set_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="EmployeePasswordRotationState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password_version", models.PositiveIntegerField(default=0)),
                ("last_rotated_at", models.DateTimeField(blank=True, null=True)),
                ("current_password_signed", models.TextField(blank=True)),
                ("user", models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="password_rotation_state", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="EmployeeSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(max_length=40, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("end_reason", models.CharField(blank=True, max_length=32)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("device_id", models.CharField(blank=True, max_length=255)),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="employee_sessions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
