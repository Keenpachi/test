from scrapy.item import Item, Field


class Product(Item):
    url = Field()
    tcin = Field()
    upc = Field()
    price_amount = Field()
    currency = Field()
    description = Field()
    specs = Field()
    ingredients = Field()
    bullets = Field()
    features = Field()


class Question(Item):
    question_id = Field()
    submission_date = Field()
    question_summary = Field()
    user_nickname = Field()
    answers = Field()
