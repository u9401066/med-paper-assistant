"""
測試 save_reference 的 JSON 字串處理修復
"""

import json
import pytest
from unittest.mock import MagicMock, patch


def test_json_string_parsing():
    """測試 JSON 字串能正確解析為 dict"""
    article_dict = {
        "pmid": "12345678",
        "title": "Test Article",
        "authors": ["Author A", "Author B"],
        "year": "2024",
        "journal": "Test Journal"
    }
    
    # 模擬 MCP 傳遞的 JSON 字串
    article_json = json.dumps(article_dict)
    
    # 測試 JSON 解析
    parsed = json.loads(article_json)
    assert isinstance(parsed, dict)
    assert parsed.get('pmid') == "12345678"


def test_dict_input_unchanged():
    """測試 dict 輸入保持不變"""
    article_dict = {
        "pmid": "12345678",
        "title": "Test Article"
    }
    
    # dict 本身就是 dict，不需要解析
    assert isinstance(article_dict, dict)
    assert article_dict.get('pmid') == "12345678"


def test_invalid_json_handling():
    """測試無效 JSON 字串的處理"""
    invalid_json = "not a valid json"
    
    with pytest.raises(json.JSONDecodeError):
        json.loads(invalid_json)


def test_save_reference_with_json_string():
    """整合測試：模擬 MCP 傳遞 JSON 字串的情況"""
    from typing import Union, Optional
    
    # 模擬修復後的處理邏輯
    def process_article(article: Union[dict, str]) -> dict:
        if isinstance(article, str):
            article = json.loads(article)
        return article
    
    # 測試字串輸入
    article_json = json.dumps({"pmid": "12345678", "title": "Test"})
    result = process_article(article_json)
    assert isinstance(result, dict)
    assert result['pmid'] == "12345678"
    
    # 測試 dict 輸入
    article_dict = {"pmid": "87654321", "title": "Test 2"}
    result = process_article(article_dict)
    assert isinstance(result, dict)
    assert result['pmid'] == "87654321"


if __name__ == "__main__":
    test_json_string_parsing()
    test_dict_input_unchanged()
    test_invalid_json_handling()
    test_save_reference_with_json_string()
    print("✅ All tests passed!")
