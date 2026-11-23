#!/usr/bin/env python3
"""Проверяет комплектность отчёта по урокам 02 и 03."""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class LessonRequirements:
    """Неизменяемые требования к комплекту сдачи одного урока."""

    report_path: Path
    screenshots_dir: Path
    screenshot_names: tuple[str, ...]
    report_fields: tuple[str, ...]


MAX_IMAGE_SIZE = 10 * 1024 * 1024
MIN_WIDTH = 640
MIN_HEIGHT = 360
MAX_DIMENSION = 12_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PLACEHOLDER_PARTS = frozenset(
    {
        "owner",
        "repo",
        "repository",
        "your-name",
        "your-repository",
        "example",
        "placeholder",
        "todo",
        "url",
    }
)
PLACEHOLDER_HOSTS = frozenset({"example.com", "example.org", "example.net", "localhost"})


def lesson_requirements(lesson: str) -> LessonRequirements:
    """Возвращает требования выбранного урока."""
    if lesson == "02":
        return LessonRequirements(
            report_path=Path("lesson_02/report.md"),
            screenshots_dir=Path("lesson_02/screenshots"),
            screenshot_names=(
                "01-project.png",
                "02-task-reservation.png",
                "03-result.png",
                "04-review.png",
                "05-completed.png",
                "06-task-product-card.png",
                "07-task-checks.png",
            ),
            report_fields=("Репозиторий", "Проект", "Задача 1", "Задача 2", "Задача 3"),
        )
    if lesson == "03":
        return LessonRequirements(
            report_path=Path("lesson_03/report.md"),
            screenshots_dir=Path("lesson_03/screenshots"),
            screenshot_names=(
                "01-questions.png",
                "02-answers.png",
                "03-requirements-v1.png",
                "04-checks-v1.png",
                "05-change.png",
                "06-requirements-v2.png",
                "07-checks-v2.png",
                "08-summary.png",
            ),
            report_fields=("Репозиторий", "Проект", "Задача"),
        )
    raise ValueError(f"Неизвестный урок: {lesson}")


LESSON_02_REQUIREMENTS = lesson_requirements("02")
REPORT_PATH = LESSON_02_REQUIREMENTS.report_path
SCREENSHOTS_DIR = LESSON_02_REQUIREMENTS.screenshots_dir
SCREENSHOT_NAMES = LESSON_02_REQUIREMENTS.screenshot_names
REPORT_FIELDS = LESSON_02_REQUIREMENTS.report_fields


def parse_url(url: str):
    """Разбирает URL и возвращает None для синтаксически неверного адреса."""
    try:
        return urlsplit(url)
    except ValueError:
        return None


def is_placeholder_url(url: str) -> bool:
    """Возвращает True для типичных незаполненных адресов."""
    parsed = parse_url(url)
    if parsed is None:
        return False
    words = re.findall(r"[a-z0-9-]+", f"{parsed.netloc}{parsed.path}".lower())
    return parsed.hostname in PLACEHOLDER_HOSTS or any(word in PLACEHOLDER_PARTS for word in words)


def is_https_url(url: str) -> bool:
    parsed = parse_url(url)
    return parsed is not None and parsed.scheme == "https" and bool(parsed.netloc)


def read_report(report: Path, requirements: LessonRequirements, errors: list[str]) -> str | None:
    if not report.exists():
        errors.append(f"Не найден отчёт: {requirements.report_path}")
        return None
    if report.is_symlink():
        errors.append(f"Отчёт не должен быть символической ссылкой: {requirements.report_path}")
        return None
    if not report.is_file():
        errors.append(f"Отчёт должен быть обычным файлом: {requirements.report_path}")
        return None
    try:
        return report.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"Отчёт должен быть текстовым UTF-8 файлом: {requirements.report_path}")
        return None


def validate_report(text: str, requirements: LessonRequirements, errors: list[str]) -> None:
    if "[[" in text or "]]" in text:
        errors.append("В отчёте остались маркеры вида [[...]].")

    values: dict[str, list[str]] = {field: [] for field in requirements.report_fields}
    fields = "|".join(re.escape(field) for field in requirements.report_fields)
    field_pattern = re.compile(rf"^\s*({fields}):\s*(\S+)\s*$")
    for line in text.splitlines():
        match = field_pattern.match(line)
        if match:
            values[match.group(1)].append(match.group(2))

    for field in requirements.report_fields:
        field_values = values[field]
        if not field_values:
            errors.append(f"Не заполнено поле «{field}: URL».")
        elif len(field_values) > 1:
            errors.append(f"Поле «{field}: URL» указано более одного раза.")
        else:
            url = field_values[0]
            if not is_https_url(url):
                errors.append(f"Поле «{field}» должно содержать HTTPS-адрес.")
            elif is_placeholder_url(url):
                errors.append(f"В поле «{field}» указан URL-заглушка.")

    repository_urls = values["Репозиторий"]
    if len(repository_urls) != 1:
        return
    repository_url = repository_urls[0]
    parsed = parse_url(repository_url)
    if parsed is None:
        return
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.hostname != "github.com"
        or parsed.query
        or parsed.fragment
        or len(path_parts) != 2
    ):
        errors.append("Поле «Репозиторий» должно иметь вид https://github.com/OWNER/REPO.")
        return

    github_repository = os.environ.get("GITHUB_REPOSITORY")
    if github_repository and "/" in github_repository:
        actual_repository = "/".join(path_parts)
        if actual_repository != github_repository:
            errors.append("Репозиторий в отчёте не совпадает с переменной GITHUB_REPOSITORY.")


def has_screenshot_link(text: str, filename: str) -> bool:
    escaped = re.escape(f"screenshots/{filename}")
    pattern = re.compile(rf"\[[^\]\n]+\]\(\s*<?{escaped}>?(?:\s+['\"][^'\"]*['\"])?\s*\)")
    return bool(pattern.search(text))


def validate_png(root: Path, image: Path, errors: list[str]) -> None:
    relative_path = image.relative_to(root)
    try:
        size = image.stat().st_size
    except OSError as exc:
        errors.append(f"Не удалось прочитать скриншот {relative_path}: {exc}")
        return

    if size == 0:
        errors.append(f"Скриншот пустой: {relative_path}")
        return
    if size > MAX_IMAGE_SIZE:
        errors.append(f"Скриншот больше 10 MiB: {relative_path}")
        return

    try:
        data = image.read_bytes()
    except OSError as exc:
        errors.append(f"Не удалось прочитать скриншот {relative_path}: {exc}")
        return

    if not is_valid_png(data):
        errors.append(f"Некорректная структура PNG: {relative_path}")
        return

    width, height = struct.unpack(">II", data[16:24])
    if not (MIN_WIDTH <= width <= MAX_DIMENSION and MIN_HEIGHT <= height <= MAX_DIMENSION):
        errors.append(
            f"Недопустимый размер {width}×{height} у скриншота {relative_path}; "
            f"нужен диапазон {MIN_WIDTH}×{MIN_HEIGHT}—{MAX_DIMENSION}×{MAX_DIMENSION}."
        )


def is_valid_png(data: bytes) -> bool:
    """Проверяет обязательные PNG-чанки, их CRC и завершение файла."""
    if not data.startswith(PNG_SIGNATURE):
        return False

    offset = len(PNG_SIGNATURE)
    first_chunk = True
    has_idat = False
    while offset < len(data):
        if len(data) - offset < 12:
            return False
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(data):
            return False
        chunk_data = data[data_start:data_end]
        expected_crc = struct.unpack(">I", data[data_end:crc_end])[0]
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
            return False
        if first_chunk:
            if chunk_type != b"IHDR" or length != 13:
                return False
            first_chunk = False
        if chunk_type == b"IDAT" and chunk_data:
            has_idat = True
        if chunk_type == b"IEND":
            return length == 0 and has_idat and crc_end == len(data)
        offset = crc_end
    return False


def validate_screenshots(
    root: Path, text: str | None, requirements: LessonRequirements, errors: list[str]
) -> None:
    screenshots = root / requirements.screenshots_dir
    if screenshots.is_symlink():
        errors.append(
            "Каталог скриншотов не должен быть символической ссылкой: "
            f"{requirements.screenshots_dir}"
        )
        return
    if not screenshots.exists() or not screenshots.is_dir():
        errors.append(f"Не найден каталог скриншотов: {requirements.screenshots_dir}")
        return

    for filename in requirements.screenshot_names:
        relative_path = requirements.screenshots_dir / filename
        image = root / relative_path
        if text is not None and not has_screenshot_link(text, filename):
            errors.append(f"В отчёте нет Markdown-ссылки на {relative_path}.")
        if not image.exists():
            errors.append(f"Не найден скриншот: {relative_path}")
            continue
        if image.is_symlink():
            errors.append(f"Скриншот не должен быть символической ссылкой: {relative_path}")
            continue
        if not image.is_file():
            errors.append(f"Скриншот должен быть обычным файлом: {relative_path}")
            continue
        validate_png(root, image, errors)


def validate(root: Path, lesson: str = "02") -> list[str]:
    """Возвращает полный список ошибок комплектности работы выбранного урока."""
    requirements = lesson_requirements(lesson)
    errors: list[str] = []
    report = root / requirements.report_path
    text = read_report(report, requirements, errors)
    if text is not None:
        validate_report(text, requirements, errors)
    validate_screenshots(root, text, requirements, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка комплекта отчёта урока")
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="корень репозитория (по умолчанию — корень этого шаблона)",
    )
    parser.add_argument(
        "--lesson",
        choices=("02", "03"),
        default="02",
        help="номер проверяемого урока (по умолчанию: 02)",
    )
    args = parser.parse_args()
    errors = validate(args.root.resolve(), args.lesson)
    if errors:
        print("Проверка не пройдена:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Проверка пройдена. Проверена только комплектность. Содержание принимает преподаватель.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
