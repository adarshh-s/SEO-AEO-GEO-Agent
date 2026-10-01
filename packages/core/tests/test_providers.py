from decimal import Decimal

from app_core.enums import AnswerEngineId
from app_core.providers.ai_answer import (
    MockAnswerEngineProvider,
    estimate_sentiment,
    match_brand,
    match_citations,
    match_competitors,
)
from app_core.providers.serp import MockSerpProvider


def test_mock_serp_provider_determinism():
    provider = MockSerpProvider()
    res1 = provider.check_ranking(
        keyword="best erp software",
        country="sa",
        language="ar",
        domain="example.com",
    )
    res2 = provider.check_ranking(
        keyword="best erp software",
        country="sa",
        language="ar",
        domain="example.com",
    )
    assert res1.position == res2.position
    assert res1.cost_usd == Decimal("0.0000")
    assert "organic" in res1.serp_features


def test_mock_serp_provider_brand_keywords():
    provider = MockSerpProvider()
    # When domain is part of keyword, ranks top 3
    res = provider.check_ranking(
        keyword="acmecorp login",
        country="us",
        language="en",
        domain="acmecorp.com",
    )
    assert res.position is not None
    assert 1 <= res.position <= 3


def test_match_brand():
    text_en = "When looking for top solutions, QuardLink is one of the highest rated platforms."
    mentioned, pos = match_brand(text_en, ["QuardLink", "quardlink.com"])
    assert mentioned is True
    assert pos == text_en.lower().find("quardlink")

    text_ar = "تعتبر منصة كوارد لينك من المنصات المتقدمة في تحسين محركات البحث."
    mentioned_ar, pos_ar = match_brand(text_ar, ["كوارد لينك", "QuardLink"])
    assert mentioned_ar is True
    assert pos_ar is not None

    not_mentioned, pos_none = match_brand("Random unrelated content.", ["QuardLink"])
    assert not_mentioned is False
    assert pos_none is None


def test_match_competitors():
    text = "Competitors include Semrush, Ahrefs, and Moz for search marketing."
    comps = ["semrush.com", "ahrefs.com", "unknowncomp.com"]
    found = match_competitors(text, comps)
    assert "semrush.com" in found
    assert "ahrefs.com" in found
    assert "unknowncomp.com" not in found


def test_match_citations():
    urls = [
        "https://en.wikipedia.org/wiki/SEO",
        "https://blog.mybrand.com/post-1",
        "https://techcrunch.com/article",
    ]
    assert match_citations(urls, "mybrand.com") is True
    assert match_citations(urls, "otherbrand.com") is False


def test_estimate_sentiment():
    pos_text = "QuardLink is an excellent, top-rated tool that leaders recommend."
    assert estimate_sentiment(pos_text, "QuardLink") == "positive"

    pos_text_ar = "تعتبر الخدمة ممتازة وأفضل حل للمؤسسات."
    assert estimate_sentiment(pos_text_ar, "الخدمة") == "positive"

    neg_text = "The product had poor customer support and was the worst experience."
    assert estimate_sentiment(neg_text, "product") == "negative"

    neutral_text = "The tool operates on cloud infrastructure."
    assert estimate_sentiment(neutral_text, "tool") == "neutral"


def test_mock_ai_answer_provider():
    provider = MockAnswerEngineProvider(AnswerEngineId.CHATGPT)
    res = provider.query(
        prompt="What is the best SEO tool for e-commerce?",
        brand_names=["QuardLink", "quardlink.com"],
        target_domain="quardlink.com",
        competitors=["semrush.com", "ahrefs.com"],
        language="en",
    )
    assert res.engine == AnswerEngineId.CHATGPT
    assert len(res.raw_answer) > 0
    assert res.cost_usd == Decimal("0.0000")
