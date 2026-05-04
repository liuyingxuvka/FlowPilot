from __future__ import annotations

import unittest

from flowpilot_cockpit.i18n import STRINGS, SUPPORT_URL, Translator


class FlowPilotCockpitI18nTests(unittest.TestCase):
    def test_chinese_table_covers_english_keys(self) -> None:
        self.assertEqual(set(STRINGS["en"]), set(STRINGS["zh"]))

    def test_translator_localizes_status(self) -> None:
        translator = Translator("zh")
        self.assertEqual(translator.status("running"), "运行中")
        translator.set_language("en")
        self.assertEqual(translator.status("complete"), "Complete")

    def test_support_url_and_copy_avoid_private_or_promise_language(self) -> None:
        self.assertEqual(SUPPORT_URL, "https://paypal.me/Yingxuliu")
        combined = " ".join(STRINGS["en"].values()) + " ".join(STRINGS["zh"].values())
        forbidden = ["donation", "email", "warranty@", "priority feature", "捐款", "邮箱", "优先功能"]
        for word in forbidden:
            self.assertNotIn(word, combined)


if __name__ == "__main__":
    unittest.main()
