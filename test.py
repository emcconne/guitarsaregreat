from pyquery import PyQuery as pq
from price_parser import Price
import urllib
import re


d = pq(url="https://www.guitarcenter.com/Used/?Ntt=martin%20D18&Ns=r")

for product in d('.listing-container .product-item').items():
    product_element = product.find('.product-name')
    title = product_element.text()
    url = product_element.attr('href')
    extended_price = product.find('.sale-price').text()
    price = Price.fromstring(extended_price)
    was = product.find('.was-price').text()
    was_price = Price.fromstring(was)
    extended_product_id = product.attr('data-product-sku-id')
    product_id = (extended_product_id[5:])
    store_name_element = product.find('.store-name-text')
    store_name = store_name_element.text()
    extended_condition = store_name_element.parents('p').nextAll().text()
    condition = (extended_condition[11:])
    print("title=" + title)
    print("price=" + price.amount_text)
    if was_price.amount != None:
        print("was=" + was_price.amount_text)
    print("condition=" + condition)
    print("product_id=" + product_id)
    print("store_name=" + store_name)
    print("url=" + url)

# for product in d('.product').items():
#     title = product.find('.productTitle').text()
#     extended_price = product.find('.productPrice').text()
#     price = Price.fromstring(extended_price)
#     reduced = product.find('.maxSavingsMSRP').text()
#     reduced_price = Price.fromstring(reduced)
#     print(type(reduced_price))
#     condition = product.find('.productCondition').text()
#     extended_product_id = product.find('.productId').text()
#     product_id = (extended_product_id[5:])

#     print("title=" + title)
#     print("price=" + price.amount_text)
#     if reduced_price.amount != None:
#         print("reduced=" + reduced_price.amount_text)
#     print("condition=" + condition)
#     print("product_id=" + product_id)

    


    
