from selenium import webdriver
from selenium.webdriver.common.by import By
import gspread
from time import sleep
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import datetime
from tempfile import mkdtemp
import json
import boto3
from google.oauth2 import service_account

# Initialize S3 client
s3_client = boto3.client("s3")


import os

DEBUG = os.getenv("DEBUG")


# Function to take a screenshot and upload it to S3
def capture_screenshot_and_upload(driver, file_name):
    if not DEBUG:
        return
    try:
        bucket_name = "autogreens-debug"
        screenshot = driver.get_screenshot_as_png()  # Capture screenshot as binary data
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=screenshot,
            ContentType="image/png"
        )
        print(f"Screenshot saved to s3://{bucket_name}/{file_name}")
    except Exception as e:
        print(f"Error uploading screenshot {file_name}: {str(e)}")

# Fetch Google API credentials JSON from AWS Secrets Manager
def get_google_credentials():
    try:
        secret_name = "my-google-api-credentials"  # Name of your secret in Secrets Manager
        region_name = "eu-west-3"  # AWS region of the Secrets Manager

        # Create a Secrets Manager client
        client = boto3.client("secretsmanager", region_name=region_name)
        
        # Retrieve the secret
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse the JSON credentials and create credentials object
        secret_json = json.loads(response["SecretString"])
        credentials = service_account.Credentials.from_service_account_info(secret_json)
        return credentials
    except Exception as e:
        print(f"Error retrieving Google credentials from Secrets Manager: {str(e)}")
        raise

# Fetch custom configuration from AWS Secrets Manager
def get_autogreens_config():
    try:
        secret_name = "autogreens-config"  # Name of your secret in Secrets Manager
        region_name = "eu-west-3"  # AWS region of the Secrets Manager

        # Create a Secrets Manager client
        client = boto3.client("secretsmanager", region_name=region_name)
        
        # Retrieve and parse the secret
        response = client.get_secret_value(SecretId=secret_name)
        config = json.loads(response["SecretString"])  # Assuming this is a JSON object
        return config
    except Exception as e:
        print(f"Error retrieving autogreens config from Secrets Manager: {str(e)}")
        raise

# Retrieve Google API credentials and apply scopes
creds = get_google_credentials()
scope = [
   'https://spreadsheets.google.com/feeds',
   'https://www.googleapis.com/auth/spreadsheets',
   'https://www.googleapis.com/auth/drive.file',
   'https://www.googleapis.com/auth/drive'
]
creds = creds.with_scopes(scope)

# Authorize the client
client = gspread.authorize(creds)

# Higher-order functions for Google Sheets operations
def create_row(sheet, data):
   sheet.append_row(data)

def read_data(sheet):
   return sheet.get_all_records()

def update_cell(sheet, row, col, new_value):
    sheet.update_cell(row, col, new_value)

def delete_row(sheet, row):
    sheet.delete_rows(row)

# Constants for column indexes
GY_MKT_UNIT = 6
GY_EXP_UNIT = 7
LAST_UPDATE_COL_MKT = 16
LAST_UPDATE_COL_EXP = 17

# XPATH Constants
# XPATH_LOGIN_USERNAME_INPUT = "/html/body/div[2]/div/div/div/form/div[1]/div[1]/input"
XPATH_LOGIN_USERNAME_INPUT = "/html/body/div[1]/main/div/div/div[2]/form/div[1]/input"
# XPATH_LOGIN_PASSWORD_INPUT = "/html/body/div[2]/div/div/div/form/div[1]/div[2]/input"
XPATH_LOGIN_PASSWORD_INPUT = "/html/body/div[1]/main/div/div/div[2]/form/div[2]/input"
# XPATH_OBSTRUCTING_ELEMENT = "/html/body/div[3]"
# XPATH_OBSTRUCTING_ELEMENT = "/html/body/div[3]"
# XPATH_LOGIN_BUTTON = "/html/body/div[2]/div/div/div/form/div[2]/input"
XPATH_LOGIN_BUTTON = "/html/body/div[1]/main/div/div/div[2]/form/div[3]/input"
# XPATH_ITEM_DATA_UNIT_PRICE = "/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[6]/table/tbody/tr[2]/td[2]"                  
XPATH_ITEM_DATA_UNIT_PRICE = "/html/body/div[1]/main/div/div/div[2]/article/section/div[1]/div/div/div[9]/div"                  
# Load configuration
config = get_autogreens_config()


# Access the parameters
GY_USERNAME_MARKET = config.get('gy_username_market')
GY_PASSWORD_MARKET = config.get('gy_password_market')
MC_USERNAME_MARKET = config.get('mc_username_market')
MC_SHOP_ID_MARKET = config.get('mc_shop_id_market')
MC_PASSWORD_MARKET = config.get('mc_password_market')
GY_USERNAME_EXPRESS = config.get('gy_username_express')
GY_PASSWORD_EXPRESS = config.get('gy_password_express')
MC_USERNAME_EXPRESS = config.get('mc_username_express')
MC_SHOP_ID_EXPRESS = config.get('mc_shop_id_express')
MC_PASSWORD_EXPRESS = config.get('mc_password_express')


def human_sleep(min_time=1, max_time=3):
   sleep_time = random.uniform(min_time, max_time)
   sleep(sleep_time)




options = webdriver.ChromeOptions()
options.binary_location = '/opt/chrome/chrome'
options.add_argument("--headless=new")
options.add_argument('--no-sandbox')
options.add_argument("--disable-gpu")
#small screen to save memory selenium
options.add_argument("--window-size=800,600")
options.add_argument("--single-process")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-dev-tools")
options.add_argument("--no-zygote")
options.add_argument(f"--user-data-dir={mkdtemp()}")
options.add_argument(f"--data-path={mkdtemp()}")
options.add_argument(f"--disk-cache-dir={mkdtemp()}")
# options.add_argument("--remote-debugging-port=9222")


def init_eos(username, password):
    driver = None
    try:
        # Initialize the Chrome driver
        service = webdriver.ChromeService("/opt/chromedriver")
        driver = webdriver.Chrome(options=options, service=service)

        # Step 1: Log in to the website
        driver.get("https://eos.firstinfresh.be/login")
        human_sleep(2, 4)
        print(username, password)

        # Enter username
        try:
            username_input = driver.find_element(By.XPATH, XPATH_LOGIN_USERNAME_INPUT)
            ActionChains(driver).move_to_element(username_input).click().perform()
            human_sleep(1, 3)
            username_input.send_keys(username)
            human_sleep(1, 3)
            print("Username entered")
        except Exception as e:
            print(f"Error entering username: {str(e)}")
            capture_screenshot_and_upload(driver, "error-username.png")
            raise

        # Enter password
        try:
            password_input = driver.find_element(By.XPATH, XPATH_LOGIN_PASSWORD_INPUT)
            ActionChains(driver).move_to_element(password_input).click().perform()
            human_sleep(1, 3)
            password_input.send_keys(password)
            human_sleep(1, 3)
            print("Password entered")
        except Exception as e:
            print(f"Error entering password: {str(e)}")
            capture_screenshot_and_upload(driver, "error-password.png")
            raise

        print(driver.page_source)  # This will print the full HTML of the current page
        capture_screenshot_and_upload(driver, "login-page.png")
        
        # element_to_remove = driver.find_element(By.XPATH, XPATH_OBSTRUCTING_ELEMENT)
        # driver.execute_script("arguments[0].parentNode.removeChild(arguments[0]);", element_to_remove)
        # print("Obstructing element removed.")
        
        # Submit the form
        try:
            login_button = driver.find_element(By.XPATH, XPATH_LOGIN_BUTTON)
            ActionChains(driver).move_to_element(login_button).click().perform()
            human_sleep(2, 4)
            print("Logged in successfully")
        except Exception as e:
            print(f"Error clicking login button: {str(e)}")
            capture_screenshot_and_upload(driver, "error-login-button.png")
            raise
        
        return driver
    
    except Exception as e:
        print(f"Error in init_eos: {str(e)}")
        if driver:
            capture_screenshot_and_upload(driver, "error-init-eos.png")
            driver.quit()
        raise


import re

def extract_price(input_string):
    # Regular expression to match the price pattern (e.g., "€ 1,79")
    price_pattern = r"€\s*\d+[.,]\d{2}"
    
    # Search for the price in the input string
    match = re.search(price_pattern, input_string)
    
    # Return the price if found, otherwise return None
    return match.group(0) if match else None


def run_eos(username, password, sheet):
    driver = None
    try:
        driver = init_eos(username, password)
        capture_screenshot_and_upload(driver, "after-init.png")
        
        data = read_data(sheet)
        i = 2
        for e in data:
            print(e)
            try:
                # Step 2: Navigate to the desired page
                driver.get(f"https://eos.firstinfresh.be/product/{e.get('GY-REF')}")
                human_sleep(3, 5)
                print(driver.page_source)  # This will print the full HTML of the current page
                capture_screenshot_and_upload(driver, f"item-{e.get('GY-REF')}.png")

                # Step 3: Scrape the required information
                try:
                    data_element = driver.find_element(By.XPATH, XPATH_ITEM_DATA_UNIT_PRICE)
                    scraped_data = data_element.text
                    print(scraped_data)
                    update_cell(sheet, i, GY_EXP_UNIT, scraped_data)
                    ct = datetime.datetime.now()
                    update_cell(sheet, i, LAST_UPDATE_COL_EXP, str(ct))
                except Exception as e:
                    print(f"Error scraping data for {e.get('GY-REF')}: {str(e)}")
                    update_cell(sheet, i, GY_EXP_UNIT, "Error")
                    ct = datetime.datetime.now()
                    update_cell(sheet, i, LAST_UPDATE_COL_EXP, "Error")
                    
            except Exception as e:
                print(f"Error processing item {e.get('GY-REF')}: {str(e)}")
                update_cell(sheet, i, GY_EXP_UNIT, "Error")
                update_cell(sheet, i, LAST_UPDATE_COL_EXP, "Error")
            
            i += 1

    except Exception as e:
        print(f"Error in run_eos: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()
    
def run_eos_mkt(username, password, sheet):
    driver = None
    try:
        driver = init_eos(username, password)
        capture_screenshot_and_upload(driver, "after-init.png")
        
        data = read_data(sheet)
        i = 2
        for e in data:
            print(e)
            try:
                # Step 2: Navigate to the desired page
                driver.get(f"https://eos.firstinfresh.be/product/{e.get('GY-REF')}")
                human_sleep(3, 5)
                print(driver.page_source)  # This will print the full HTML of the current page
                capture_screenshot_and_upload(driver, f"item-{e.get('GY-REF')}.png")

                # Step 3: Scrape the required information
                try:
                    data_element = driver.find_element(By.XPATH, XPATH_ITEM_DATA_UNIT_PRICE)
                    scraped_data = data_element.text
                    print(scraped_data)
                    update_cell(sheet, i, GY_MKT_UNIT, scraped_data)
                    ct = datetime.datetime.now()
                    update_cell(sheet, i, LAST_UPDATE_COL_MKT, str(ct))
                except Exception as e:
                    print(f"Error scraping data for {e.get('GY-REF')}: {str(e)}")
                    update_cell(sheet, i, GY_MKT_UNIT, "Error")
                    ct = datetime.datetime.now()
                    update_cell(sheet, i, LAST_UPDATE_COL_MKT, "Error")
                    
            except Exception as e:
                print(f"Error processing item {e.get('GY-REF')}: {str(e)}")
                update_cell(sheet, i, GY_MKT_UNIT, "Error")
                update_cell(sheet, i, LAST_UPDATE_COL_MKT, "Error")
            
            i += 1

    except Exception as e:
        print(f"Error in run_eos_mkt: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()  





def handler(event, context):
    try:
        # SHEET WITH NAME "MARKET" AND "EXPRESS"
        # sheet_market = client.open('AUTOGREENS').get_worksheet(0)
        sheet_express = client.open('DIALNA-ASSORTIMENT').get_worksheet(0)
        # run_eos(GY_USERNAME_MARKET, GY_PASSWORD_MARKET, sheet_market)
        # run_mc(MC_USERNAME_MARKET, MC_PASSWORD_MARKET, sheet_market, MC_SHOP_ID_MARKET)
        # sheet_market.sort((PRIJS_VERSHIL_COL, 'des'))
        run_eos_mkt(GY_USERNAME_MARKET, GY_PASSWORD_MARKET, sheet_express)
        # run_mc(MC_USERNAME_EXPRESS, MC_PASSWORD_EXPRESS, sheet_express, MC_SHOP_ID_EXPRESS)
        # sheet_express.sort((PRIJS_VERSHIL_COL, 'des'))

        return {
            "statusCode": 200,
            "body": "OK"
        }
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }





