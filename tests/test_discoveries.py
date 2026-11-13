import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import discoveries

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.item = dict(id='test', product_key='Example-Model', category='desk', experience='found', title='<example>', summary='Example only', source_url='https://example.com/item', checked_at='2026-01-01', affiliate=False, pros=['Documented feature'], cons=['Not tested'])

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
        for field, value in [('source_url', 'javascript:alert(1)'), ('source_url','https://user:password@example.com'), ('checked_at','2999-01-01'), ('affiliate','false'), ('affiliate',0), ('pros',[]), ('cons',None), ('experience','review'), ('product_key',''), ('seller_url','javascript:alert(1)')]:
            item = copy.deepcopy(self.item); item[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                discoveries.validate({'version': 1, 'items': [item]})

    def test_unknown_relationship_is_explicit_not_no_affiliation(self):
        self.item['affiliate'] = None
        discoveries.validate({'version': 1, 'items': [self.item]})
        rendered = discoveries.item_card(self.item)
        self.assertIn('제휴·협찬 관계 미확인', rendered)
        self.assertNotIn('제휴 관계 없음', rendered)
        del self.item['affiliate']
        with self.assertRaises(ValueError): discoveries.validate({'version': 1, 'items': [self.item]})

    def test_duplicate_model_and_tracking_url_are_rejected(self):
        for changes in [dict(product_key='ＥＸＡＭＰＬＥ Model',source_url='https://other.example/item'), dict(product_key='Another-Model',source_url='https://example.com/item/?utm_source=new&variant=white#details')]:
            duplicate = dict(self.item, id='another', **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                discoveries.validate({'version': 1, 'items': [self.item, duplicate]})

    def test_different_seller_item_numbers_are_not_duplicates(self):
        first = dict(self.item,source_url='https://shop.example/item?goodsCode=123')
        second = dict(self.item,id='second',product_key='Other-Model',source_url='https://shop.example/item?goodsCode=456')
        discoveries.validate({'version': 1, 'items': [first,second]})

    def test_populated_page_and_seller_price_are_safe(self):
        self.item.update(seller_url='https://shop.example/item?x=1&y=2',price_note='<18,600원> + 배송비 2,500원')
        page = discoveries.page({'version': 1, 'items': [self.item]}, '/')
        self.assertNotIn('현재 등록된 상품은 없습니다', page)
        self.assertIn('&lt;18,600원&gt;',page)
        self.assertIn('https://shop.example/item?x=1&amp;y=2',page)
        self.assertIn('판매처 확인하기 (새 탭)',page)
        self.assertIn('1개의 발견',discoveries.teaser('/',1))

    def image(self):
        return dict(file='static/discoveries/example.png', alt='<Product image>', credit='Brand official image', source_url='https://example.com/media', permission='press_editorial', permission_url='https://example.com/press', permission_note='Distributed for editorial coverage.', checked_at='2026-01-01', width=1980, height=1020)

    def test_image_metadata_and_deployment_prefix(self):
        self.item['image']=self.image()
        data={'version':1,'items':[self.item]}
        discoveries.validate(data)
        for prefix in ['/', '/dogu-life-preview/']:
            page=discoveries.page(data,prefix)
            self.assertIn('src="'+prefix+'static/discoveries/example.png"',page)
            self.assertIn('alt="&lt;Product image&gt;"',page)
            self.assertIn('Brand official image',page)
            self.assertNotIn('discovery-photo-pending',page)

    def test_reject_unverified_or_unsafe_images(self):
        for field,value in [('file','../private.png'),('file','https://example.com/image.png'),('file','static/discoveries/file.svg'),('permission','unknown'),('permission_url','javascript:alert(1)'),('permission_note',''),('credit',''),('alt',''),('width',0),('height',True),('checked_at','2999-01-01')]:
            self.item['image']=self.image();self.item['image'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                discoveries.validate({'version':1,'items':[self.item]})

    def test_no_image_uses_official_photo_link_without_fabricating_picture(self):
        card=discoveries.item_card(self.item)
        self.assertIn('공식 상품 사진 보기',card)
        self.assertNotIn('<img',card)
