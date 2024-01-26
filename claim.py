import time
import random
import requests

from loguru import logger
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from twocaptcha import TwoCaptcha
from ezcaptcha import EzCaptcha

from settings import (
    SAVE_LOG_FILE,
    SAVE_CLAIM_RESULT_SCREENSHOT,
    PROVIDER_CAPTCHA,
    API_KEY,
    ACCOUNT_FILE,
    PROXY_FILE,
    CHANGE_IP,
    CHANGE_IP_URL
)


def get_addresses():
    logger.info("Read addresses file")
    try:
        with open(ACCOUNT_FILE, 'r') as f:
            claim_list = f.readlines()
    except Exception as e:
        logger.error(e)

    return claim_list

def get_proxies():
    logger.info("Read proxies file")
    try:
        with open(PROXY_FILE, 'r') as f:
            proxies = f.readlines()
    except Exception as e:
        logger.error(e)

    return proxies

def get_2captcha_token():
    try:
        result = solver.recaptcha(
            sitekey='6LfOA04pAAAAAL9ttkwIz40hC63_7IsaU2MgcwVH',
            url='https://artio.faucet.berachain.com/',
            action='submit',
            score=0.5,
            version='v3')
    except Exception as e:
        logger.error(f'Captcha error:{e}')
        return False

    return result['code']


def get_ezcaptcha_token():
    try:
        result = solver.solve({
            "websiteURL": "https://artio.faucet.berachain.com/",
            "websiteKey": '6LfOA04pAAAAAL9ttkwIz40hC63_7IsaU2MgcwVH',
            "type": 'RecaptchaV3TaskProxyless',
            "isInvisible": True,
            "pageAction": 'submit'
        })
    except Exception as e:
        logger.error(f'Captcha error:{e}')
        return False

    if result['errorId'] > 0:
        error_code = result['errorCode']
        error_desc = result['errorDesc']

        logger.error(f'Captcha error [{error_code}]:{error_desc}')
        return False

    return result['token']


def get_captcha_token():
    if PROVIDER_CAPTCHA == '2captcha':
        return get_2captcha_token()
    else:
        return get_ezcaptcha_token()


def get_result(browser, retry):
    time.sleep(3)

    try:
        browser.find_element(By.CSS_SELECTOR, '.bg-success')
        return True
    except NoSuchElementException:
        logger.warning('Retry get claim status. Wait 10 seconds')

        time.sleep(7)

        if retry:
            get_result(browser, False)
        else:
            return False


def get_proxy_options(proxy, proxy_type='http', verify=False):
    return {
        'proxy': {
            proxy_type: proxy,
            'verify_ssl': verify,
        },
    }


def claim(address, proxy_options):
    logger.info(f'Start claim {address}')

    chrome_options = webdriver.ChromeOptions()
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument("--use_subprocess")
    chrome_options.add_argument('--no-sandbox')

    logger.info(f'Open browser {address} and wait 2 seconds')
    browser = webdriver.Chrome(options=chrome_options, seleniumwire_options=proxy_options)
    browser.get('https://artio.faucet.berachain.com/')
    time.sleep(2)

    # agree terms
    logger.info(f'Agree terms and wait 1 seconds')
    try:
        browser.find_element(By.CSS_SELECTOR, '[data-state="unchecked"]').click()
    except ElementClickInterceptedException:
        logger.error('Current IP not access denied')
        browser.quit()
        return False
    except NoSuchElementException:
        logger.error('Site unavailable')
        browser.quit()
        return False

    try:
        browser.find_element(By.CSS_SELECTOR, '[data-state="open"] button.bg-primary').click()
    except ElementClickInterceptedException:
        logger.error('Agree error')

        if SAVE_CLAIM_RESULT_SCREENSHOT:
            browser.save_screenshot(f'agree_error_{time.time()}.png')

        browser.quit()
        return False

    time.sleep(1)

    # first button
    browser.find_element(By.CSS_SELECTOR, 'input:first-child').send_keys(address)
    browser.find_element(By.CSS_SELECTOR, 'button.bg-primary').click()
    logger.info(f'First button clicked')

    # resolve captcha
    logger.info(f'Wait resolve captcha...')
    token = get_captcha_token()

    if not token:
        browser.close()
        return False

    script = """
        ___grecaptcha_cfg.clients['100000']['T']['T']['promise-callback']('%s')
    """ % token

    browser.execute_script(script)  # run callback captcha (for safety)
    logger.info(f'Resolved captcha and wait 3 seconds...')

    time.sleep(3)

    # second button
    browser.find_element(By.CSS_SELECTOR, 'button.bg-primary').click()
    logger.info(f'Second button clicked and wait 3 seconds')

    claim_success = get_result(browser, True)

    if claim_success:
        logger.success(f'Wallet {address} claimed')
    else:
        try:
            danger_text = browser.find_element(By.CSS_SELECTOR, '.bg-destructive').text
        except NoSuchElementException:
            danger_text = 'Unknown'

        logger.error(f'Wallet {address} not claimed: {danger_text}')

    if SAVE_CLAIM_RESULT_SCREENSHOT:
        browser.save_screenshot(f'{address}.png')

    browser.quit()
    return True


if __name__ == '__main__':
    if PROVIDER_CAPTCHA == '2captcha':
        solver = TwoCaptcha(API_KEY)
    else:
        solver = EzCaptcha(client_key=API_KEY)

    if SAVE_LOG_FILE:
        logger.add('claim.log')

    proxies = get_proxies()
    proxy = random.choice(proxies)
    proxy_options = get_proxy_options(proxy.strip())
    addresses = get_addresses()

    for address in addresses:
        claim(address.strip(), proxy_options)
        sleep_time = random.randint(40, 80)
        logger.info(f'Pause. Wait next wallet {sleep_time} seconds')
        time.sleep(sleep_time)

        if CHANGE_IP:
            requests.get(CHANGE_IP_URL)
