"""Stage 15: swearing starred in burned captions and hooks, as production does (cases from its policy tests)."""
import pytest

from smtv_core.render.profanity import mask, masked


@pytest.mark.parametrize("text,expected", [
    ("Ебучая хуйня, заебательно и #пиздец", "Е**чая х**ня, з**бательно и #п**дец"),
    ("су-ка, е6учий, xуйня", "с*-*а, е**чий, x**ня"),
    ("съебаться, въебал, ebuchaya", "с**баться, в**бал, e**chaya"),
    ("BLYAT and fucking shit", "B**AT and f**king s**t"),
    ("бляблябля после обычного слова", "б**блябля после обычного слова"),
    ("пидорас и чурка", "п**орас и ч**ка"),
    ("ЗА ПОПКУ ТРОГАЛ, БЛЯДЬ, НАХУЙ", "ЗА ПОПКУ ТРОГАЛ, Б**ДЬ, Н**УЙ"),
])
def test_swearing_is_starred_like_in_production(text, expected):
    assert mask(text) == expected


def test_ordinary_words_stay():
    text = ("жопа, жопу, жопой, небо, себя, вебинар, ebay, Huion, бляшка, хулиган, страхует, мудрый, мандарин, сукно, Нигерия, "
            "жидкость, хачапури, педикюр, гей, транс, трансляция и fooBITCHbar")
    assert mask(text) == text


def test_caption_words_keep_their_times():
    words = [{"text": "ну", "s": 0, "e": 100}, {"text": "блядь,", "s": 100, "e": 300}]
    assert masked(words) == [{"text": "ну", "s": 0, "e": 100}, {"text": "б**дь,", "s": 100, "e": 300}]
