from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import (
    parse_allowed_hosts,
    parse_boolean_setting,
    resolve_allowed_hosts,
    resolve_secret_key,
)


class EnvironmentConfigurationTests(SimpleTestCase):
    """Unit tests for Issue #29 environment parsing and safe defaults."""

    def test_boolean_setting_uses_default_when_unset(self):
        self.assertTrue(parse_boolean_setting(None, name="DJANGO_DEBUG", default=True))
        self.assertFalse(parse_boolean_setting(None, name="DJANGO_DEBUG", default=False))

    def test_boolean_setting_accepts_common_true_and_false_values(self):
        for value in ("true", "TRUE", "yes", "on", "1"):
            with self.subTest(value=value):
                self.assertTrue(parse_boolean_setting(value, name="FLAG", default=False))
        for value in ("false", "FALSE", "no", "off", "0"):
            with self.subTest(value=value):
                self.assertFalse(parse_boolean_setting(value, name="FLAG", default=True))

    def test_boolean_setting_rejects_invalid_values(self):
        with self.assertRaises(ImproperlyConfigured):
            parse_boolean_setting("sometimes", name="DJANGO_DEBUG", default=False)

    def test_allowed_hosts_are_split_and_trimmed(self):
        self.assertEqual(
            parse_allowed_hosts(" localhost, 127.0.0.1 ,,example.test "),
            ["localhost", "127.0.0.1", "example.test"],
        )

    def test_allowed_hosts_reject_empty_value(self):
        with self.assertRaises(ImproperlyConfigured):
            parse_allowed_hosts(" ,  ")

    def test_allowed_hosts_use_local_defaults_only_in_debug(self):
        self.assertEqual(
            resolve_allowed_hosts(None, debug=True), ["127.0.0.1", "localhost"]
        )

    def test_allowed_hosts_are_required_when_debug_is_disabled(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_allowed_hosts(None, debug=False)

    def test_wildcard_hosts_are_rejected_when_debug_is_disabled(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_allowed_hosts("*", debug=False)

    def test_secret_key_uses_configured_value(self):
        configured_key = "s" * 50
        self.assertEqual(
            resolve_secret_key(f" {configured_key} ", debug=False), configured_key
        )

    def test_secret_key_rejects_example_placeholder(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("replace-with-a-generated-secret-key", debug=False)

    def test_secret_key_requires_minimum_length_in_production(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("too-short", debug=False)

    def test_secret_key_has_local_only_fallback_in_debug(self):
        self.assertIn("local-development-only", resolve_secret_key("", debug=True))

    def test_secret_key_is_required_when_debug_is_disabled(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key(None, debug=False)
