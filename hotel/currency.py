"""Валюта відображення: en → USD ($), uk → UAH (₴).

У базі ціни зберігаються в USD; для української мови суми конвертуються
за фіксованим курсом USD_TO_UAH (поміняй курс тут, якщо потрібно).
"""
from decimal import Decimal, ROUND_HALF_UP

# Курс USD → UAH для відображення цін українською
USD_TO_UAH = Decimal("44.78")

SYMBOLS = {"en": "$", "uk": "₴"}


def lang_symbol(lang):
    """Знак валюти для мови (за замовчуванням — $)."""
    return SYMBOLS.get(lang, "$")


def convert_usd(value, lang):
    """Конвертує суму з USD у валюту мови (uk → грн)."""
    if value is None or value == "":
        amount = Decimal("0")
    else:
        try:
            amount = Decimal(str(value))
        except Exception:
            amount = Decimal("0")
    if lang == "uk":
        amount = amount * USD_TO_UAH
    return amount


def format_amount(amount, decimals=2):
    """Число з розділювачем тисяч і потрібною кількістю знаків: 1234.5 → 1,234.50."""
    decimals = int(decimals)
    quantum = Decimal(1).scaleb(-decimals)
    amount = amount.quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{amount:,.{decimals}f}"


def money_str(value, lang, decimals=2):
    """Готовий рядок: «$504.00» (en) або «₴20,916.00» (uk)."""
    return f"{lang_symbol(lang)}{format_amount(convert_usd(value, lang), decimals)}"
