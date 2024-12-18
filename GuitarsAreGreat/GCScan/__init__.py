from pyquery import PyQuery as pq
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from price_parser import Price
import azure.functions as func
import datetime
import logging
import os

class Product:
    def __init__(self, id, model, price, original_price, title, condition):
        self.id = id
        self.model = model
        self.price = price
        self.original_price = original_price
        self.condition = condition
        self.title = title

class Criteria:
    def __init__(self, model, low_price, high_price, extra_words, not_words):
        self.model = model
        self.low_price = low_price
        self.high_price = high_price
        self.extra_words = extra_words
        self.not_words = not_words

COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
GC_USED_URL = os.environ["GC_USED_URL"]
#Prices taken from dropdown on GC website
price_range=[25,50,100,200,300,500,750,1000,1500,2000,3000,5000,7500,15000,50000]
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
partition_key_path = PartitionKey(path="/id")
db = client.create_database_if_not_exists(id="GuitarCenter")
criteria_container = db.create_container_if_not_exists(id="Criteria", partition_key=partition_key_path, offer_throughput=400)
item_container = db.create_container_if_not_exists(id="Items", partition_key=partition_key_path, offer_throughput=400)

def main(mytimer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function started')
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
    try:
        queryGuitarCenter()
    except Exception as e:
        logging.error('An error occurred: %s', e)

def set_price_range_url_option(low_price, high_price):
    # These values are defined in the min/max boxes for prices on GC website
    price_url_string=""
    if low_price==0 and high_price==0:
        return price_url_string
    if low_price:
        low_position_in_range=find_lower_number(price_range,low_price)
    if high_price:
        high_position_in_range=find_higher_number(price_range,high_price)
    if not high_price:
        high_position_in_range=15
    if not low_price:
        low_position_in_range=1
    # range below has +1 added since python stops at top of range and doesn't include it by default
    for num in range(low_position_in_range, high_position_in_range+1):
        price_url_string += str(1080+num) + "+"
    return "&N=" + price_url_string.rstrip("+")

def find_higher_number(arr, num):
    for i in range(len(arr)):
        if arr[i] >= num:
            # return position without including 0
            return i+1
    return -1

def find_lower_number(arr, num):
    for i in range(len(arr)):
        if arr[i] <= num:
            continue
        else:
            # return position without including 0
            return i+1
    return -1

def build_list_from_string(s):
    return s.split()

def build_string_from_list(lst, sep):
    return sep.join(lst)

def find_word_in_string(s, word):
    return word in s

def search_words(string, word_list):
    string = string.lower()
    for word in word_list:
        if word.lower() in string:
            return True
    return False

def match_at_least_one(title, word_list):
    for word in word_list:
        if word.lower() in title.lower().split():
            return True
    return False

def match_all(s, word_list):
    s = s.lower().split()
    for word in word_list:
        if word.lower() not in s:
            return False
    return True

def qualified_product(criteria, product):
    if criteria.high_price != 0 or criteria.low_price != 0:
        if criteria.high_price <= criteria.low_price:
            raise Exception("Price Criteria Incorrectly set for {}", criteria.model) 
        if product.price >= criteria.high_price or product.price < criteria.low_price:
            return False
    if criteria.extra_words is not None:
        if not match_all(product.title, build_list_from_string(criteria.extra_words)):
            return False
    if criteria.not_words is not None:
        if match_at_least_one(product.title, build_list_from_string(criteria.not_words)):
            return False
    if not match_at_least_one(product.condition, ["Fair","Good","Great","Excellent"]):
        return False
    return True

def parse_gc_html(model, gc_url):
    matching_models = []
    for product in gc_url('.listing-container .product-item').items():
        product_element = product.find('.product-name')
        title = product_element.text()
        url = product_element.attr('href')
        extended_price = product.find('.sale-price').text()
        price = Price.fromstring(extended_price).amount_float
        was = product.find('.was-price').text()
        original_price = Price.fromstring(was).amount_float
        extended_product_id = product.attr('data-product-sku-id')
        product_id = (extended_product_id[5:])
        store_name_element = product.find('.store-name-text')
        store_name = store_name_element.text()
        extended_condition = store_name_element.parents('p').nextAll().text()
        condition = (extended_condition[11:]) 
        found_product = Product(id=product_id, model=model, price=price, original_price=original_price, title=title, condition=condition)
        matching_models.append(found_product)
    return matching_models


def add_new_item(container, product):
    new_item = {
        "id": product.id,
        "model": product.model,
        "title": product.title,
        "ignored": False,
        "price": product.price,
        "original_price": product.original_price,
        "condition": product.condition
    }
    try:
        existing_item = container.read_item(
            item=product.id,
            partition_key=product.id
        )
        if existing_item["price"] > product.price:
            existing_item["ignored"] = False
            existing_item["price"] = product.price
            container.replace_item(item=existing_item, body=existing_item)
    except CosmosResourceNotFoundError:
        try:
            container.create_item(body=new_item)
            logging.info('Added new item to database: %s:%s', product.id, product.title)
        except Exception as e:
            logging.error('An error occurred: %s', e)

def queryGuitarCenter():
    # Create a CosmosClient instance using the connection string
    logging.info('Starting GC Query Execution')
    try:
        query = "SELECT * FROM c WHERE c.Disabled = false"
        result_iterable = criteria_container.query_items(query, enable_cross_partition_query=True)
        for criteria_item in result_iterable:
            criteria = Criteria(criteria_item.get("Model"), criteria_item.get("LowPrice"), criteria_item.get("HighPrice"), criteria_item.get("ExtraSearchItems"), criteria_item.get("NotWords"))
            model = criteria.model
            gc_url = GC_USED_URL + build_string_from_list(build_list_from_string(criteria.model),"%20") + set_price_range_url_option(criteria.low_price, criteria.high_price) + "&recsPerPage=90"
            gc_html = pq(url=gc_url)
            products = parse_gc_html(model, gc_html)
            for p in products:
                if qualified_product(criteria, p):
                    add_new_item(item_container, p)
    except Exception as e:
        logging.error('An error occurred: %s', e)
