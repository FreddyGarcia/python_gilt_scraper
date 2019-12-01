import re
import requests
import bs4
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36',
    'Host': 'www.gilt.com'
}

BASE_URL = 'https://www.gilt.com/api/'


def request(url):
    res = requests.get(url, headers=HEADERS)
    return res


def get_cities() -> list:
    res = request(BASE_URL + 'v3/city')
    json_data = json.loads(res.text)
    cities = json_data['data']
    return cities


def get_products_by_city(city_id: int, page_no=0) -> list:
    res = request(BASE_URL + f'v3.4/catalog/products?pageSize=200&hideSoldOut=false&boutiqueContextId={city_id}&page={page_no}')
    json_data = json.loads(res.text)
    products = json_data['data']
    next_page = json_data['meta'].get('next')
    number_of_pages = json_data['meta']['totalPages']

    def get_product_id(product):
        return str(product['id'])

    print (f'Page {page_no + 1} of {number_of_pages}')
    products = list(map(get_product_id, products))

    if next_page:
        page_no += 1
        products += get_products_by_city(city_id, page_no)
    
    return products


def product_info(product_id: int) -> dict:
    res = request(BASE_URL + 'v3/products/' + product_id)
    json_data = json.loads(res.text)
    product = json_data['data']

    def set_address(product: dict):
        locations = product['locations']

        if len(locations) > 0 and len(locations[0]['addresses']) > 0:
            address = locations[0]['addresses'][0]
            product['city'] = address.get('city', '')
            product['address2'] = address.get('address2', '')
            product['state'] = address.get('state', '')
            product['address'] = address.get('address', '')
            product['zip'] = address.get('postalCode', '')

    def set_image(product: dict):

        try:
            colors = product['attributes']['colors']
            if len(colors) > 0:

                if len(colors[0]['images_detail']) > 0:
                    image = colors[0]['images_detail'][0]
                elif len(colors[0]['images_alt']) > 0:
                    image = colors[0]['images_alt'][0]
                elif len(colors[0]['images_tablet']) > 0:
                    image = colors[0]['images_tablet'][0]
                else:
                    image = ''
        except Exception as e:
            image = ''

        product['image'] = image

    def set_sku(product: dict):

        skus = product['skus']
        if len(skus) > 0:
            sku = skus[0]
            product['terms'] = sku.get('terms', '')
            product['price'] = int(sku.get('price', '0')) / 100
            product['originalPrice'] = int(sku.get('msrp', '0')) / 100

            try:
                features = sku.get('features').replace('\ufeff', '').replace('\xa0','')
                expiration_date_pattern = '|'.join((
                    'redeem by',
                    'redeemed by',
                    'redemption begins',
                    'completed by',
                    'redeemed on',
                    'booked by',
                    'completed by',
                    'redeem on',
                    'must be used by',
                    'valid from',
                ))
                date_of_redeem = re.search('(' + expiration_date_pattern + ')(?P<a>[\w, ]*\d{4})', features, re.IGNORECASE)
                date_of_redeem = date_of_redeem.groupdict().get('a', '').strip()
                product['expirationDate'] = date_of_redeem
            except Exception as e:
                product['expirationDate'] = ''


    set_image(product)
    set_address(product)
    set_sku(product)

    boutique = product.get('boutiqueId')
    id = product.get('id')

    product_data = {
        'id': product.get('id'),
        'url': f'https://www.gilt.com/boutique/product/{boutique}/{id}',
        'storeName': product.get('brand'),
        'dealSaving': product.get('name'),
        'description': product.get('shortDescription'),
        'originalPrice': product.get('listPriceMin'),
        'originalPrice': product.get('originalPrice'),
        'expirationDate': product.get('expirationDate'),
        'terms': product.get('terms'),
        'price': product.get('price'),
        'image': product.get('image'),
        'city': product.get('city'),
        'address2': product.get('address2'),
        'state': product.get('state'),
        'address': product.get('address'),
        'zip': product.get('zip')
    }

    return product_data


def scrape_products() -> list:

    cities = get_cities()
    products = []

    print(f'{len(cities)} cities found')

    for city in cities:
        city_name = city['name']
        print(f'Searching products in "{city_name}" ')
        city_id = city['contextId']
        append_products = get_products_by_city(city_id)
        print(f'{len(append_products)} products found in {city_name}')
        products += append_products
    
    print(f'Total: {len(products)} products found')
    return products


def get_products():
    for product_id in scrape_products():
        product = product_info(product_id)
        yield product


if __name__ == "__main__":
    for product in get_products():
        print(product)  
