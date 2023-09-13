from scrapy import Request, Spider
from syndigo.items import Product, Question
import re
import json


class Target(Spider):
    name = 'target_scraper'

    def __init__(self, url=None, *args, **kwargs):
        self.url = url
        self.api_key = None
        self.tcin = None
        super(Target, self).__init__(*args, **kwargs)

    def start_requests(self):
        yield Request(url=self.url, callback=self.parse_product)

    def parse_product(self, response):
        self.api_key = re.search(r'apiKey\\":\\"(\d+\w+)\\",\\"baseUrl', response.text).group(1)
        # prepare raw data
        raw_data = re.findall(r'JSON.parse\((.+)\)', response.text)[2][:-1]
        # convert raw data
        data = json.loads(json.loads(raw_data))
        # handle products with many versions
        if 'product' in data['__PRELOADED_QUERIES__']['queries'][0][1]:
            index = 0
        else:
            index = 2

        self.tcin = data['__PRELOADED_QUERIES__']['queries'][index][0][1]['tcin']
        product_data = data['__PRELOADED_QUERIES__']['queries'][index][1]['product']

        price_amount_raw = product_data['price']['formatted_current_price']
        if '$' in price_amount_raw:
            currency = 'USD'
        else:
            currency = 'Unknown'

        # handle products with many versions
        if 'children' in product_data:
            for child in product_data['children']:
                price_amount_raw = child['price']['formatted_current_price']
                if '$' in price_amount_raw:
                    currency = 'USD'
                else:
                    currency = 'Unknown'

                product = Product()
                product['url'] = response.url
                product['tcin'] = child['tcin']
                product['upc'] = child['item']['primary_barcode']
                product['price_amount'] = price_amount_raw[1:]
                product['currency'] = currency
                product['description'] = child['item']['product_description']['downstream_description']
                product['specs'] = None
                product['ingredients'] = []
                product['bullets'] = ''.join(child['item']['product_description']['soft_bullets']['bullets'])
                product['features'] = [x.replace('<B>', '').replace('</B>', '') for x in child['item']['product_description']['bullet_descriptions']]

                yield product
        else:
            product = Product()
            product['url'] = response.url
            product['tcin'] = self.tcin
            product['upc'] = product_data['item']['primary_barcode']
            product['price_amount'] = price_amount_raw[1:]
            product['currency'] = currency
            product['description'] = product_data['item']['product_description']['downstream_description']
            product['specs'] = None
            product['ingredients'] = []
            product['bullets'] = ''.join(product_data['item']['product_description']['soft_bullets']['bullets'])
            product['features'] = [x.replace('<B>', '').replace('</B>', '') for x in product_data['item']['product_description']['bullet_descriptions']]

            yield product

        # get Q&A
        questions_url = f'https://r2d2.target.com/ggc/Q&A/v1/question-answer?key={self.api_key}&page=0&questionedId={self.tcin}&type=product&size=10'

        yield Request(url=questions_url, callback=self.parse_questions)

    def parse_questions(self, response):
        data = response.json()

        for answer in data['results']:
            if 'nickname' in answer['author']:
                nick = answer['author']['nickname']
            else:
                nick = None

            question = Question()
            question['question_id'] = answer['id']
            question['submission_date'] = answer['submitted_at']
            question['question_summary'] = answer['text']
            question['user_nickname'] = nick
            question['answers'] = [{'answer_id': response['id'], 'answer_summary': response['text'], 'submission_date': response['submitted_at'], 'user_nickname': response['author']['nickname']} for response in answer['answers']]

            yield question

        # get next Q&A page
        last_page = data['last_page']
        current_page = data['page']

        if not last_page:
            questions_url = f'https://r2d2.target.com/ggc/Q&A/v1/question-answer?key={self.api_key}&page={current_page + 1}&questionedId={self.tcin}&type=product&size=10'

            yield Request(url=questions_url, callback=self.parse_questions)
