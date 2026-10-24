import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import discoveries

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.item = dict(id='test', category='desk', experience='found', title='<example>', summary='Example only', source_url='https://example.com/item', checked_at='2026-01-01', affiliate=False, pros=['Documented feature'], cons=['Not tested'])

    def test_empty_shelf_has_no_product_links(self):
        page = discoveries.page({'version': 1, 'items': []}, '/')
        self.assertIn('현재 등록된 상품은 없습니다', page)
        self.assertNotIn('target="_blank"', page)
        self.assertNotIn('구매하기', page)

    def test_usage_evidence_and_safe_links(self):
        data = {'version': 1, 'items': [self.item]}
        discoveries.validate(data)
        rendered = discoveries.item_card(self.item)
        self.assertIn('미사용 발견', rendered)
        self.assertIn('&lt;example&gt;', rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)
        self.item.update(experience='used', affiliate=True)
        with self.assertRaises(ValueError): discoveries.validate(data)
        self.item['usage_notes'] = 'Actual usage notes'
        discoveries.validate(data)
        rendered = discoveries.item_card(self.item)
        self.assertIn('직접 사용', rendered)
        self.assertIn('noopener noreferrer sponsored', rendered)
        self.assertIn('수수료', rendered)

    def test_reject_missing_and_unsafe_evidence(self):
        for field, value in [('source_url', 'javascript:alert(1)'), ('source_url','https://user:password@example.com'), ('checked_at','2999-01-01'), ('affiliate',None), ('pros',[]), ('cons',None), ('experience','review')]:
            item = copy.deepcopy(self.item); item[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                discoveries.validate({'version': 1, 'items': [item]})
