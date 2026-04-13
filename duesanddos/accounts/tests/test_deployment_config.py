from pathlib import Path

from django.test import SimpleTestCase


class ElasticBeanstalkConfigTests(SimpleTestCase):
    def test_collectstatic_runs_on_every_instance_when_static_is_local(self):
        config_path = (
            Path(__file__).resolve().parents[2] / ".ebextensions" / "01-migrate.config"
        )
        config_text = config_path.read_text()

        self.assertIn("02_collectstatic:", config_text)
        self.assertNotIn(
            (
                "02_collectstatic:\n    command: "
                '"python manage.py collectstatic --noinput"\n'
                "    leader_only: true"
            ),
            config_text,
        )
