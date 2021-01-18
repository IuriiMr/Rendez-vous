
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import DesiredCapabilities

from selenium import webdriver

import time
import io
import random
import requests
import sys

from stem import Signal
from stem.control import Controller
from stem.process import *
from bs4 import BeautifulSoup
import speech_recognition as sr
from pydub import AudioSegment


def recaptcha():
    # Randomization Related
    MIN_RAND = 0.64
    MAX_RAND = 1.27
    LONG_MIN_RAND = 4.78
    LONG_MAX_RAND = 11.1

    # from https://www.houndify.com/ free account
    HOUNDIFY_CLIENT_ID = 'ID'
    HOUNDIFY_CLIENT_KEY = 'KEY'

    # Check box
    WebDriverWait(browser, 30).until(ec.frame_to_be_available_and_switch_to_it(
        (By.CSS_SELECTOR, "iframe[name^='a-'][src^='https://www.google.com/recaptcha/api2/anchor?']")))
    check_box = WebDriverWait(browser, 30).until(ec.element_to_be_clickable((By.ID, "recaptcha-anchor")))
    check_box.click()
    time.sleep(random.uniform(LONG_MIN_RAND, LONG_MAX_RAND))
    browser.switch_to.default_content()
    WebDriverWait(browser, 30).until(ec.frame_to_be_available_and_switch_to_it(
        (By.XPATH,'//iframe[@title="recaptcha challenge"]')))
    audio_button = WebDriverWait(browser, 30).until(ec.element_to_be_clickable(
        (By.XPATH, '//*[@id="recaptcha-audio-button"]')))

    # Switch to the audio version
    audio_button.click()
    time.sleep(random.uniform(LONG_MIN_RAND, LONG_MAX_RAND))

    # Get the audio challenge URI from the download link
    download_object = browser.find_element_by_xpath('//*[@id="audio-source"]')
    download_link = download_object.get_attribute('src')

    # Download the challenge audio and store in memo
    request = requests.get(download_link)
    audio_file = io.BytesIO(request.content)

    # Convert the audio to a compatible format in memory
    converted_audio = io.BytesIO()
    sound = AudioSegment.from_mp3(audio_file)
    sound.export(converted_audio, format="wav")
    converted_audio.seek(0)

    # Initialize a new recognizer with the audio in memory as source
    recognizer = sr.Recognizer()
    with sr.AudioFile(converted_audio) as source:
        audio = recognizer.record(source)  # read the entire audio file

    # recognize speech using Google Speech Recognition
    try:
        #audio_output = recognizer.recognize_google(audio, language = "fr-FR")
        #print("Google Speech Recognition: " + audio_output)

        # Check if we got harder audio captcha
        #if any(character.isdigit() or character.isupper() for character in audio_output):
            # Use Houndify to detect the harder audio captcha
        audio_output = recognizer.recognize_houndify(
            audio, client_id=HOUNDIFY_CLIENT_ID, client_key=HOUNDIFY_CLIENT_KEY)
        print("Houndify Speech to Text: " + audio_output)

    except sr.UnknownValueError or sr.RequestError:
        print("Google Speech Recognition could not understand audio")
        audio_output = recognizer.recognize_houndify(
            audio, client_id=HOUNDIFY_CLIENT_ID, client_key=HOUNDIFY_CLIENT_KEY)
        print("Houndify Speech to Text: " + audio_output)

    # Enter the audio challenge solution
    browser.find_element_by_id('audio-response').send_keys(audio_output)
    time.sleep(random.uniform(MIN_RAND, MAX_RAND))

    # Click on verify
    browser.find_element_by_id('recaptcha-verify-button').click()
    time.sleep(random.uniform(MIN_RAND, MAX_RAND))
    print('ReCaptcha passed')


def switchIP():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)
        time.sleep(2)
        browser.delete_all_cookies()
        print('SwitchIP')


def printIP():
    browser.get("http://checkip.dyndns.org/")
    html = browser.page_source
    soup = BeautifulSoup(html, 'lxml')
    body = str(soup.find('body'))[6:-7]
    print(body, end="")
    browser.get("http://www.geoplugin.net/json.gp?ip=" + body[20:])
    html = browser.page_source
    soup = BeautifulSoup(html, 'lxml')
    country = eval(soup.pre.text)['geoplugin_countryName']
    print(country)


def proxy(PROXY_HOST, PROXY_PORT):
    fp = webdriver.FirefoxProfile()
    # Direct = 0, Manual = 1, PAC = 2, AUTODETECT = 4, SYSTEM = 5
    fp.set_preference("network.proxy.type", 1)
    fp.set_preference("network.proxy.socks", PROXY_HOST)
    fp.set_preference("network.proxy.socks_port", int(PROXY_PORT))
    fp.set_preference("dom.webdriver.enabled", False)
    fp.set_preference('useAutomationExtension', False)
    fp.set_preference('devtools.jsonview.enabled', False)
    fp.update_preferences()
    options = Options()
    desired = DesiredCapabilities.FIREFOX

    return webdriver.Firefox(options=options, firefox_profile=fp, desired_capabilities=desired)

# Define TOR process to get connected to the web  only from France
tor_process = stem.process.launch_tor_with_config(
    config={
        'ControlPort': '9051',
        'SOCKSPort': '9050',
        'ExitNodes': '{fr}',
        'StrictNodes': '1',
        'Log': [
            'NOTICE stdout',
            'ERR file /tmp/tor_error_log',
        ],
    },
)

browser = proxy("127.0.0.1", 9050)

# Set up links
bobigny = 'http://www.seine-saint-denis.gouv.fr/booking/create/9829'
raincy = 'http://www.seine-saint-denis.gouv.fr/booking/create/10317'
training = 'http://www.seine-saint-denis.gouv.fr/booking/create/9845'
attempt = 0

# Telegram api token
api_token = 'API_TOKEN'
chat_id = 'CHAT_ID'


def send_message_telegram(message):
    response = requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token),
                 params={'chat_id': chat_id, 'text': message})
    return response.json()


def check_page_loaded():
    WebDriverWait(browser, 45).until(ec.presence_of_all_elements_located((By.XPATH, '//h1')))
    h1 = browser.find_element_by_xpath('//h1').text
    while (re.search('50\d', h1)):
        browser.refresh()
        time.sleep(2)
        try:
            browser.switch_to.alert.accept()
        except NoAlertPresentException:
            pass
        time.sleep(random.random() * 10 + 1)
        try:
            h1 = browser.find_element_by_xpath('//h1').text
        except Exception:
            continue

def check_forbidden():
    h1 = browser.find_element_by_xpath('//h1').text
    while (re.search('Forbidden', h1)):
        switchIP()
        time.sleep(2)
        browser.refresh()
        try:
            browser.switch_to.alert.accept()
        except NoAlertPresentException:
            pass
        time.sleep(random.random() * 10 + 1)
        try:
            h1 = browser.find_element_by_xpath('//h1').text
        except Exception:
            continue


def accept_cookies():
    time.sleep(1)
    cookies_appears = browser.find_element_by_xpath("//a[text()='Accepter']").is_displayed()
    if cookies_appears:
        browser.find_element_by_xpath("//a[text()='Accepter']").click()
        WebDriverWait(browser, 5).until(ec.invisibility_of_element((By.ID, 'cookies-banner')))


def wait_check():
    time.sleep(random.random() * 10 + 10)
    check_page_loaded()
    check_forbidden()
    accept_cookies()


def first_page():
    # Accept conditions of the 1st page and go to the next
    browser.find_element_by_id('condition').click()
    browser.find_element_by_name('nextButton').click()
    WebDriverWait(browser, 45).until(ec.url_changes)


def next_page():
    # Click at the default choice
    browser.find_element_by_name('nextButton').click()


def fourth_page():

    recaptcha()
    print('Done')
    browser.switch_to.default_content()
    time.sleep(5)
    browser.find_element_by_name('nextButton').click()

def fifth_page():

    browser.switch_to.default_content()
    browser.find_element_by_name("firstname").send_keys(FIRST_NAME)
    time.sleep(2)
    browser.find_element_by_name("lastname").send_keys(LAST_NAME)
    time.sleep(3)
    browser.find_element_by_name("email").send_keys(EMAIL)
    time.sleep(2)
    browser.find_element_by_name("emailcheck").send_keys(EMAIL)


def check_mail():
    import imaplib
    import email
    import re

    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(EMAIL, 'password')

    mail.list()
    mail.select("inbox")

    result, data = mail.search(None, '(SUBJECT "Demande de rendez-vous en attente de confirmation")')

    ids = data[0]
    id_list = ids.split()
    latest_email_id = id_list[-1]

    result, data = mail.fetch(latest_email_id, "(RFC822)")
    raw_email = data[0][1]
    raw_email_string = raw_email.decode('utf-8')

    email_message = email.message_from_string(raw_email_string)
    if email_message.is_multipart():
        for payload in email_message.get_payload():
            body = payload.get_payload(decode=True).decode('utf-8')
    else:
        body = email_message.get_payload(decode=True).decode('utf-8')

    confirmation_link = re.search("(?P<url>https?://[^\s]+)", body).group("url")
    mail.unsubscribe('prisederdvaes@gmail.com')

    return confirmation_link


def confirm_rdv(confirmation_link):
    browser.get(confirmation_link)
    WebDriverWait(browser, 45).until(ec.url_changes)

    time.sleep(3)
    recaptcha()
    browser.switch_to.default_content()
    browser.find_element_by_name("email").send_keys(email)

    WebDriverWait(browser, 30).until(ec.element_to_be_clickable((By.ID, 'submit_Booking')))
    browser.find_element_by_id('submit_Booking').click()
    WebDriverWait(browser, 45).until(ec.url_changes)

    print('Confirmed')
    time.sleep(3)

def send_rdv():
    browser.get('http://gmail.com')
    emailElem = browser.find_element_by_id('identifierId')
    emailElem.send_keys('prisederdvaes@gmail.com')
    nextButton = browser.find_element_by_id('identifierNext')
    nextButton.click()
    time.sleep(1)

    passwordElem = browser.find_element_by_name('password')
    passwordElem.send_keys('password')
    signinButton = browser.find_element_by_id('passwordNext')
    signinButton.click()
    time.sleep(10)

    messages = browser.find_elements_by_xpath("//div [@class='y6']/span")
    for message in messages:
        if 'Validation de la demande de rendez-vous' in message.text:
            print(message.text)
            message.click()
            break

    confirmation = browser.find_elements_by_xpath("//a[text()='Cliquez ici pour confirmer cette demande de rendez-vous']")[0]
    confirmation_link = confirmation.get_attribute('href')

    print(confirmation_link)

    logout1 = browser.find_elements_by_css_selector(".gb_Ia")[0]
    logout1.click()
    time.sleep(2)
    logout2 = browser.find_element_by_css_selector("#gb_71")
    logout2.click()
    WebDriverWait(browser, 45).until(ec.url_changes)

    return confirmation_link


# Check TOR process at the start
browser.get('https://check.torproject.org')
browser.delete_all_cookies()
printIP()

# Check 2 subprefectures for RDV
while True:

    # Choose target link
    if attempt % 2 == 0:
        target = bobigny
    # target = training
    else:
        target = raincy

    # Open AES form in browser
    browser.get(target)
    wait_check()
    first_page()
    wait_check()

    # Extract the text from the result page
    time.sleep(20)
    WebDriverWait(browser, 45).until(ec.presence_of_all_elements_located((By.XPATH, '//*[@id="FormBookingCreate"]')))
    text = browser.find_element_by_xpath('//*[@id="FormBookingCreate"]').text

    # Check if the text contain the information about free time slot
    no_free_slot = (re.search("Il n'existe plus de plage horaire libre pour votre demande de rendez-vous.", text))
    attempt += 1

    # Change IP after 100 calls
    if attempt % 100 == 0:
        switchIP()
        browser.delete_all_cookies()

    # Print attempt number, Is there a free time slot, time of the request
    print(attempt, (no_free_slot is None), time.ctime())

    # Send message if there is a free time slot to fill in the form
    if no_free_slot is None:
        send_message_telegram("Filling in the form!")

        # Filling the form
        browser.maximize_window()
        next_page()
        time.sleep(3)

        next_page()
        time.sleep(3)

        next_page()
        time.sleep(4)

        fourth_page()
        time.sleep(3)

        fifth_page()
        time.sleep(3)

        tor_process.kill()
        sys.exit()

    # Wait about 150 sec for each form and repeat
    time.sleep(random.random() * 20 + 50)
    browser.find_element_by_name('finishButton').click()


if __name__ == '__main__':
    main()

