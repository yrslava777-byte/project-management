"""Unit-тесты проверки комплекта отчёта lesson_02."""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import check_submission as checker


def png(width: int = 640, height: int = 360) -> bytes:
    """Создаёт маленький корректный PNG заданных размеров для фикстуры."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = (b"\x00" + b"\x00\x00\x00\xff" * width) * height
    return (
        checker.PNG_SIGNATURE
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class CheckSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {"GITHUB_REPOSITORY": "student/project-management"})
        environment.start()
        self.addCleanup(environment.stop)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.screenshots = self.root / checker.SCREENSHOTS_DIR
        self.screenshots.mkdir(parents=True)
        for filename in checker.SCREENSHOT_NAMES:
            (self.screenshots / filename).write_bytes(png())
        self.write_valid_report()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_valid_report(self) -> None:
        links = "\n".join(
            f"- [Скриншот](screenshots/{filename})"
            for filename in checker.SCREENSHOT_NAMES
        )
        (self.root / checker.REPORT_PATH).write_text(
            "\n".join(
                (
                    "Репозиторий: https://github.com/student/project-management",
                    "Проект: https://portal.bitrix24.ru/workgroups/group/1/tasks/",
                    "Задача 1: https://portal.bitrix24.ru/company/personal/user/1/tasks/task/view/1/",
                    "Задача 2: https://portal.bitrix24.ru/company/personal/user/1/tasks/task/view/2/",
                    "Задача 3: https://portal.bitrix24.ru/company/personal/user/1/tasks/task/view/3/",
                    "",
                    links,
                    "",
                )
            ),
            encoding="utf-8",
        )

    def errors(self) -> list[str]:
        return checker.validate(self.root)

    def write_valid_lesson_03_submission(self) -> None:
        requirements = checker.lesson_requirements("03")
        screenshots = self.root / requirements.screenshots_dir
        screenshots.mkdir(parents=True)
        for filename in requirements.screenshot_names:
            (screenshots / filename).write_bytes(png())
        links = "\n".join(
            f"- [Скриншот](screenshots/{filename})"
            for filename in requirements.screenshot_names
        )
        (self.root / requirements.report_path).write_text(
            "\n".join(
                (
                    "Репозиторий: https://github.com/student/project-management",
                    "Проект: https://portal.bitrix24.ru/workgroups/group/1/tasks/",
                    "Задача: https://portal.bitrix24.ru/company/personal/user/1/tasks/task/view/1/",
                    "",
                    links,
                    "",
                )
            ),
            encoding="utf-8",
        )

    def test_valid_submission_passes(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_valid_lesson_03_submission_passes(self) -> None:
        self.write_valid_lesson_03_submission()
        self.assertEqual(checker.validate(self.root, "03"), [])

    def test_blank_lesson_03_report_is_rejected(self) -> None:
        self.write_valid_lesson_03_submission()
        requirements = checker.lesson_requirements("03")
        (self.root / requirements.report_path).write_text("", encoding="utf-8")
        errors = checker.validate(self.root, "03")
        self.assertTrue(any("Не заполнено поле" in error for error in errors))

    def test_missing_lesson_03_screenshot_is_rejected(self) -> None:
        self.write_valid_lesson_03_submission()
        requirements = checker.lesson_requirements("03")
        (self.root / requirements.screenshots_dir / "08-summary.png").unlink()
        errors = checker.validate(self.root, "03")
        self.assertTrue(any("08-summary.png" in error for error in errors))

    def test_empty_screenshot_is_rejected(self) -> None:
        (self.screenshots / checker.SCREENSHOT_NAMES[0]).write_bytes(b"")
        self.assertTrue(any("пустой" in error for error in self.errors()))

    def test_placeholder_url_is_rejected(self) -> None:
        report = self.root / checker.REPORT_PATH
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "https://github.com/student/project-management",
                "https://github.com/OWNER/REPO",
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("заглушка" in error for error in self.errors()))

    def test_missing_screenshot_link_is_rejected(self) -> None:
        report = self.root / checker.REPORT_PATH
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                f"[Скриншот](screenshots/{checker.SCREENSHOT_NAMES[0]})",
                checker.SCREENSHOT_NAMES[0],
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("Markdown-ссылки" in error for error in self.errors()))

    def test_non_png_file_is_rejected(self) -> None:
        (self.screenshots / checker.SCREENSHOT_NAMES[0]).write_bytes(b"not a PNG")
        self.assertTrue(any("Некорректная структура PNG" in error for error in self.errors()))

    def test_truncated_png_is_rejected(self) -> None:
        image = self.screenshots / checker.SCREENSHOT_NAMES[0]
        image.write_bytes(image.read_bytes()[:24])
        self.assertTrue(any("Некорректная структура PNG" in error for error in self.errors()))

    def test_invalid_url_is_reported_without_crashing(self) -> None:
        report = self.root / checker.REPORT_PATH
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "https://portal.bitrix24.ru/workgroups/group/1/tasks/",
                "https://[",
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("HTTPS-адрес" in error for error in self.errors()))

    def test_small_dimensions_are_rejected(self) -> None:
        (self.screenshots / checker.SCREENSHOT_NAMES[0]).write_bytes(png(639, 359))
        self.assertTrue(any("Недопустимый размер" in error for error in self.errors()))

    def test_non_github_repository_is_rejected(self) -> None:
        report = self.root / checker.REPORT_PATH
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "https://github.com/student/project-management",
                "https://gitlab.com/student/project-management",
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("должно иметь вид" in error for error in self.errors()))

    def test_repository_must_match_github_actions_environment(self) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "other/project"}):
            self.assertTrue(any("не совпадает" in error for error in self.errors()))

    def test_symlinked_screenshot_is_rejected(self) -> None:
        image = self.screenshots / checker.SCREENSHOT_NAMES[0]
        image.unlink()
        image.symlink_to(checker.SCREENSHOT_NAMES[1])
        self.assertTrue(any("символической ссылкой" in error for error in self.errors()))

    def test_oversized_screenshot_is_rejected(self) -> None:
        image = self.screenshots / checker.SCREENSHOT_NAMES[0]
        image.write_bytes(png() + b"x" * checker.MAX_IMAGE_SIZE)
        self.assertTrue(any("больше 10 MiB" in error for error in self.errors()))

    def test_non_https_report_url_is_rejected(self) -> None:
        report = self.root / checker.REPORT_PATH
        report.write_text(
            report.read_text(encoding="utf-8").replace(
                "https://portal.bitrix24.ru/workgroups/group/1/tasks/",
                "http://portal.bitrix24.ru/workgroups/group/1/tasks/",
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("HTTPS-адрес" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
