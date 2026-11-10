import os.path
import random

from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import time
from selenium.webdriver.chrome.service import Service as ChromeService, Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import csv
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from PIL import Image
from email import encoders
import html
import Litmus_Common_Functions


class CsvFileReader():
    def __init__(self, filename):
        with open(filename, "r") as f_input:
            csv_input = csv.reader(f_input)
            self.details = list(csv_input)

    def get_row_col(self, row, col):
        return self.details[row][col]


class CsvLogWriter():
    def writeText(self, filename, text_to_append):
        try:
            filenamestr = str(filename)
            with open(filenamestr, 'a') as f:
                file = csv.writer(f)
                f.write(text_to_append + '\n')
        except:
            print("Can't append to the file")


class RemoveFile:
    def removeFile(self, filename):
        strfilename = filename
        if os.path.exists(strfilename):
            os.remove(strfilename)


class DefineLocatorsBy:
    def locatorValue(self, type, value):
        if type == 'ID':
            by = By.ID, value
        elif type == 'CSS_SELECTOR':
            by = By.CSS_SELECTOR, value
        elif type == 'XPATH':
            by = By.XPATH, value
        elif type == 'CLASS_NAME':
            by = By.CLASS_NAME, value
        elif type == 'TAG_NAME':
            by = By.TAG_NAME, value
        elif type == 'LINK_TEXT':
            by = By.LINK_TEXT, value
        elif type == 'PARTIAL_LINK_TEXT':
            by = By.PARTIAL_LINK_TEXT, value
        elif type == 'NAME':
            by = By.NAME, value
        return by


class WebApplicationActions:

    def clickElement(self, locator):
        try:
            element = driver.find_element(*locator)
            element.click()
            time.sleep(7)
        except:
            print("Can't find specified element for CLICK")
            global exception_counter
            exception_counter = exception_counter + 1

    def doubleclickElement(self, locator):
        try:
            print(locator)
            element = driver.find_element(*locator)
            print(element)
            actions = ActionChains(driver)
            actions.double_click(element).perform()
            print('after actions')
            time.sleep(4)
        except:
            print("Can't find specified element for double click")
            global exception_counter
            exception_counter = exception_counter + 1

    def waitForElementAndClick(self, locator, time):
        try:
            print(locator)
            int_time = int(time)
            element = WebDriverWait(driver, int_time).until(EC.presence_of_element_located(locator))
            print(element)
            element.click()
        except:
            print("Can't find specified element")
            global exception_counter
            exception_counter = exception_counter + 1

    def getToastText(self, locator, range1, range2):
        try:
            element = driver.find_element(*locator)
            toastText = element.text
            toastTextstr = str(toastText)
            numrange1 = int(range1)
            numrange2 = int(range2)
            required_text = toastTextstr[numrange1:numrange2]
            return (required_text)
        except:
            print("Can't get toast")
            global exception_counter
            exception_counter = exception_counter + 1

    def sendText(self, locator, text_data):
        if text_data != 'GLOBAL_VALUE':
            str_text_data = str(text_data)
        else:
            global textholder
            print(textholder)
            text_data = textholder
            str_text_data = str(text_data)
            print(str_text_data)
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            element.send_keys(text_data)
            time.sleep(7)
        except:
            print("Can't find specified element for entering text")
            global exception_counter
            exception_counter = exception_counter + 1

    def sendTextKeyENTER(self, locator, text_data):
        if text_data != 'GLOBAL_VALUE':
            str_text_data = str(text_data)
        else:
            global textholder
            text_data = textholder
            str_text_data = str(text_data)
            print(str_text_data)
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            print(locator)
            print(element)
            actions = ActionChains(driver)
            actions.move_to_element(element).send_keys(str_text_data).send_keys(Keys.ENTER).perform()
            print('after actions move')
            time.sleep(4)
        except:
            print("Can't find specified element for entering text")
            global exception_counter
            exception_counter = exception_counter + 1

    def sendKeyENTER(self, locator, key_name):
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            actions = ActionChains(driver)
            actions.move_to_element(element).send_keys(Keys.ENTER).perform()
            time.sleep(4)
        except:
            print("Can't find specified element for enter")
            global exception_counter
            exception_counter = exception_counter + 1

    def scrollToElement(self, scrollbyValue, locator=None):
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            actions = ActionChains(driver)
            actions.move_to_element(element).perform()
            time.sleep(4)
        except:
            print("Can't scroll")
            global exception_counter
            exception_counter = exception_counter + 1

    def scrollDown(self):
        try:
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            time.sleep(4)
        except:
            print("Can't scroll vertically")
            global exception_counter
            exception_counter = exception_counter + 1

    def sendKeyDOWN(self, locator, key_name):
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            actions = ActionChains(driver)
            actions.move_to_element(element).send_keys(Keys.DOWN).perform()
            time.sleep(4)
        except:
            print("Can't find specified element for down")
            global exception_counter
            exception_counter = exception_counter + 1

    def acceptAlert(self):
        try:
            obj = driver.switch_to.alert
            obj.accept()

        except:
            print("Can't find alert")
            global exception_counter
            exception_counter = exception_counter + 1

    def sendTextWithTimeStamp(self, locator, text_data):
        str_text_data = str(text_data)
        str_text_data_with_timestamp = str_text_data + "_" + datetime.datetime.now().strftime('%H_%M')
        print(str_text_data_with_timestamp)
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            element.send_keys(str_text_data_with_timestamp)
            time.sleep(5)
        except:
            print("Can't find specified element for entering Text")
            global exception_counter
            exception_counter = exception_counter + 1

    def clearText(self, locator):
        try:
            element = driver.find_element(*locator)
            # element.clear()
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
        except:
            print("Can't find specified element for clearing text")
            global exception_counter
            exception_counter = exception_counter + 1

    def getAttribute(self, locator, attribute_name):
        try:
            element = driver.find_element(*locator)
            attribute_value = element.get_attribute(attribute_name)
            return str(attribute_value)
        except:
            print("Can't find specified element for retrieving name attribute")
            global exception_counter
            exception_counter = exception_counter + 1

    def getAttributeFromSvg(self, locator, attribute_name):
        try:
            element = driver.find_element(*locator)
            element_svg = element.find_element_by_xpath(".//*[name()='svg']")
            attribute_value = element_svg.get_attribute(attribute_name)
            return str(attribute_value)
        except:
            print("Can't find specified element for retrieving svg attribute")
            global exception_counter
            exception_counter = exception_counter + 1

    def getText(self, locator):
        try:
            element = driver.find_element(*locator)
            elementtext = element.text
            global textholder
            textholder = elementtext
            print(textholder)
        except:
            print("Can't find specified element for retrieving text attribute")
            global exception_counter
            exception_counter = exception_counter + 1

    def checkText(self, locator, test_string):
        try:
            str_test_string = str(test_string)
            element = driver.find_element(*locator)
            elementtext = element.text
            if str_test_string in elementtext:
                comparision_result = "PASSED"
                return comparision_result
            else:
                comparision_result = "FAILED"
                return comparision_result
        except:
            print("Can't find specified element for retrieving text attribute")
            global exception_counter
            exception_counter = exception_counter + 1

    def getTextAndSaveInGlobalDic(self, locator, keyname):
        element = driver.find_element(*locator)
        elementvalue = element.get_attribute('innerHTML')
        add_dic = {keyname: elementvalue}
        key_value.update(add_dic)

    def getValueFromGlobalDic(self, keyname):
        keyvalue = key_value.get(keyname)
        return keyvalue

    def checkPopup(self, locator):
        time.sleep(5)
        try:
            driver.switch_to.active_element
            time.sleep(2)
            alert_popup = driver.find_element(*locator)
            if alert_popup is not None:
                try:
                    alert_popup.click()
                    time.sleep(4)
                except:
                    pass
            else:
                pass
        except:
            print("Can't find popup for click")
            global exception_counter
            exception_counter = exception_counter + 1

    def expandEnterKeyOnAutoCompleteDropdown(self, locator):
        try:
            expand_arrow = driver.find_element(*locator)
            actions = ActionChains(driver)
            actions.move_to_element(expand_arrow).click().send_keys(Keys.ENTER).perform()
            time.sleep(4)
        except:
            print("Can't select first option of autocomplete dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def hoverAndClick(self, locator):
        try:
            hover_element = driver.find_element(*locator)
            actions = ActionChains(driver)
            actions.move_to_element(hover_element).perform()
            actions.click(hover_element).perform()
            time.sleep(4)
        except:
            print("Can't hover and click on element")
            global exception_counter
            exception_counter = exception_counter + 1

    def autoCompleteDropdownMultipleSelectionFirstOption(self, locator):
        try:
            expand_arrow = driver.find_element(*locator)
            actions = ActionChains(driver)
            actions.move_to_element(expand_arrow).click().perform()
            value = driver.find_element_by_id('downshift-1-item-0')
            value.click()
        except:
            print("Can't select first option of autocomplete multiple selection dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def openURL(self, url):
        driver.get(url)
        time.sleep(5)

    # def uploadFile(self, locator, uploadfilepath):
    # try:
    # print(locator)
    # upload_element = driver.find_element(*locator)
    # print(uploadfilepath)
    # actions = ActionChains(driver)
    # actions.move_to_element(upload_element).click().send_keys(uploadfilepath).perform()
    # time.sleep(5)
    # except:
    # print("Can't upload file")
    # global exception_counter
    # exception_counter = exception_counter + 1

    def addSleep(self, sleep_time):
        int_sleep_time = int(sleep_time)
        time.sleep(int_sleep_time)

    def switchToActiveElement(self):
        time.sleep(2)
        driver.switch_to.active_element
        time.sleep(4)

    def autoCompleteDropDownEnterTextFirstOption(self, locator, text):
        try:
            expand_arrow = driver.find_element(*locator)
            actions = ActionChains(driver)
            actions.move_to_element(expand_arrow).click().perform()
            actions.move_to_element(expand_arrow).send_keys(text).perform()
            actions.move_to_element(expand_arrow).send_keys(Keys.ENTER).perform
        except:
            print("Can't select first option after entering text in autocomplete dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def autoCompleteDropDownHidden(self, locator, text):
        try:
            time.sleep(3)
            expand_arrow = driver.find_element(*locator)
            actions = ActionChains(driver)
            actions.move_to_element(expand_arrow).click().perform()
            actions.move_to_element(expand_arrow).send_keys(text).perform()
            time.sleep(5)
            outermenu = driver.find_element_by_class_name('Select-menu-outer')
            details = outermenu.get_attribute('innerHTML')
            value = driver.find_element_by_css_selector('div.Select-option.is-focused')
            value.click()
            time.sleep(4)
        except:
            print("Can't select first option after entering text in hidden autocomplete dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def enterValueDropDownOption(self, locator, text):
        try:
            expand_arrow = driver.find_element(*locator)
            actions = ActionChains(driver)
            actions.move_to_element(expand_arrow).click().send_keys(text).send_keys(Keys.ENTER).perform()
        except:
            print("Can't select first option after entering text from autocomplete dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def screenShot(self):
        try:
            screenshotfilename = datetime.datetime.now().strftime('%H_%M%p%B%d') + '.png'
            driver.save_screenshot(screenshots_file_path + '\\' + screenshotfilename)
            time.sleep(4)
        except:
            print("Can't take screenshot")
            global exception_counter
            exception_counter = exception_counter + 1

    def filterValueFromDropDownList(self, dropdownlocator, filter_value):
        try:
            expand = driver.find_element(*dropdownlocator).get_attribute("aria-expanded")
            if expand == 'false':
                driver.find_element(*dropdownlocator).click()
                time.sleep(3)
            dropdownlist = []
            dropdownlist = driver.find_elements_by_css_selector('li.select2-results__option')
            for list_item in dropdownlist:
                dropdownlistvalue = list_item.get_attribute('innerHTML')
                if filter_value == dropdownlistvalue:
                    list_item.click()
                    time.sleep(5)
                    break
                else:
                    pass
        except:
            print("Can't filter in dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def setCalendarDate(self, date_locators, select_date_value):
        try:
            dateslist = []
            dateslist = driver.find_elements(*date_locators)
            for list_item in dateslist:
                fetched_datevalue = list_item.text
                if select_date_value == fetched_datevalue:
                    list_item.click()
                    time.sleep(5)
                    break
                else:
                    pass
        except:
            print("Can't select date in calendar")
            global exception_counter
            exception_counter = exception_counter + 1

    def filterOnNthValueFromDropDownList(self, dropdownlocator, nthlistlocator):
        try:
            expand = driver.find_element(*dropdownlocator).get_attribute("aria-expanded")
            if expand == 'false':
                driver.find_element(*dropdownlocator).click()
                time.sleep(3)
                driver.find_element(*nthlistlocator).click()
                time.sleep(5)
        except:
            print("Can't filter on Nth Value in dropdown list")
            global exception_counter
            exception_counter = exception_counter + 1

    def drag_drop(self, draglocator, droplocator):
        try:
            screenShot()
            dragsource = driver.find_element(*draglocator)
            print(dragsource)
            droptarget = driver.find_element(*droplocator)
            print(droptarget)
            action = ActionChains(driver)
            action.drag_and_drop_by_offset(dragsource, 50, 40).perform()
            time.sleep(5)
            screenShot()
        except:
            print("Can't drag drop")
            global exception_counter
            exception_counter = exception_counter + 1

    def filterOnNthValue(self, dropdownlocator, nthlistlocator):
        try:
            expand = driver.find_element(*dropdownlocator).get_attribute("aria-expanded")
            if expand == 'false':
                driver.find_element(*dropdownlocator).click()
                time.sleep(3)
                driver.find_element(*nthlistlocator).click()
                time.sleep(5)
        except:
            print("Can't filter on Nth Value")
            global exception_counter
            exception_counter = exception_counter + 1

    def searchableDropdown(self, locator, option_text):
        """
        Works with searchable dropdowns.
        Clicks input -> types text -> waits -> presses Enter.
        """

        try:
            element = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable(locator)
            )

            # Scroll into view
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                element
            )

            # Click input
            element.click()

            # Clear previous value
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)

            # Type required option
            element.send_keys(option_text)

            # Wait for options
            time.sleep(1)

            # Select first matching option
            element.send_keys(Keys.ARROW_DOWN)
            element.send_keys(Keys.ENTER)

            time.sleep(1)

        except Exception as e:
            print(f"Searchable dropdown failed : {e}")
            global exception_counter
            exception_counter += 1

    def selectFromDropDownMenuOptions(self, menuoptionslocators, filter_value):
        try:
            expand = driver.find_element(*menuoptionslocators).click()
            dropdownlist = []
            dropdownlist = driver.find_elements(*menuoptionslocators)
            print(dropdownlist)
            for menu_item in dropdownlist:
                dropdownlistvalue = menu_item.get_attribute('innerHTML')
                if filter_value == dropdownlistvalue:
                    menu_item.click()
                    time.sleep(10)
                    break
                else:
                    pass
        except:
            print("Can't select from dropdown menu")
            global exception_counter
            exception_counter = exception_counter + 1

    def companyLogout(self, locator):
        try:
            all_buttons = driver.find_elements(*locator)
            all_buttons[6].click()
            time.sleep(3)
        except:
            print("Can't Logout")
            global exception_counter
            exception_counter = exception_counter + 1

    def selectCheckboxFromDropDownList(self, dropdownlocator, dropdownlistlocators, filter_value):
        try:
            expand = driver.find_element(*dropdownlocator).get_attribute("aria-expanded")
            if expand == 'false':
                driver.find_element(*dropdownlocator).click()
                time.sleep(3)
            dropdownlist = []
            dropdownlist = driver.find_elements_by_xpath(dropdownlistlocators)
            for list_item in dropdownlist:
                dropdownlistvalue = list_item.text
                if filter_value == dropdownlistvalue:
                    list_item.find_element_by_css_selector('input.mr-1').click()
                    time.sleep(5)
                    break
                else:
                    pass
        except:
            print("Can't select checkbox in dropdownlist")
            global exception_counter
            exception_counter = exception_counter + 1

    def selectRadioButtonFromList(self, dropdownlistlocators, filter_value):
        try:
            dropdownlist = []
            dropdownlist = driver.find_elements(*dropdownlistlocators)
            for list_item in dropdownlist:
                dropdownlistvalue = list_item.getAttribute('label.option')
                if filter_value == dropdownlistalue:
                    list_item.find_element_by_class_name("payment_information[payment_method]").click()
                    time.sleep(5)
                    break
                else:
                    pass
        except:
            print("Can't select radio  button")
            global exception_counter
            exception_counter = exception_counter + 1

    def clickOnNthRow(self, rownumber):
        try:
            rowintable = driver.find_element_by_xpath(
                "//div[@id='app']/section/div[2]/div[2]/section[2]/div/table/tbody/tr[" + str(
                    rownumber) + "]/td/table/tbody/tr/td[1]/a")
            if rowintable is not None:
                rowintable.click()
                time.sleep(7)

        except:
            try:
                rowsvg = driver.find_element_by_xpath(
                    "//div[@id='app']/section/div[2]/div[2]/section[2]/div/table/tbody/tr[" + str(
                        rownumber) + "]/td[1]")
                clickableitem = rowsvg.find_element_by_css_selector("svg.cursor-pointer")
                if clickableitem is not None:
                    clickableitem.click()
                    time.sleep(7)

            except:
                try:
                    spanhrefclick = driver.find_element_by_xpath(
                        "//div[@id='app']/section/div[2]/div[2]/section[2]/div/table/tbody/tr[" + str(
                            rownumber) + "]/td[1]/span/a")
                    if spanhrefclick is not None:
                        spanhrefclick.click()
                        time.sleep(7)

                except:
                    try:
                        spanhrefclick = driver.find_element_by_xpath(
                            "//div[@id='app']/section/div[2]/div[2]/section[2]/div[1]/table/tbody/tr[" + str(
                                rownumber) + "]/td[1]/a")
                        if spanhrefclick is not None:
                            spanhrefclick.click()
                            time.sleep(7)

                    except:
                        try:
                            editlinkintable = driver.find_element_by_xpath(
                                "//div[@id='app']/section/div[2]/div[2]/section[2]/div/table/tbody/tr[" + str(
                                    rownumber) + "]/td/table/tbody/tr/td[2]/a[1]")
                            if editlinkintable is not None:
                                editlinkintable.click()
                                time.sleep(7)
                        except:
                            print("Can't click on Nth row")
                            global exception_counter
                            exception_counter = exception_counter + 1

    def clickOnSecondColumnOfNthRow(self, rownumber):
        try:
            spanhrefclicksecond = driver.find_element_by_xpath(
                "//div[@id='app']/section/div[2]/div[2]/section[2]/div/table/tbody/tr[" + str(
                    rownumber) + "]/td[2]/span/a")

            if spanhrefclicksecond is not None:
                spanhrefclicksecond.click()
                time.sleep(7)

        except:
            print("Can't click on second column of Nth row")
            exception_counter = exception_counter + 1

    def getList(self, filename, loc_header, loc_listname, loc_parenttablerow, loc_parenttable, loc_allchildtable,
                loc_childtabledata):
        try:
            filenamestr = str(filename)
            with open(filenamestr, 'a') as f:
                file = csv.writer(f)
                header = driver.find_elements(*loc_header)
                myheader = []
                for h in header:
                    header_text = h.text
                    myheader.append(header_text)
                f.write(
                    "============================================================================================\n")
                name = driver.find_element(*loc_listname).get_attribute('innerHTML')
                f.write(name + '\n')

                table_id = driver.find_element(*loc_parenttable)
                rows = table_id.find_elements(*loc_allchildtable)  # get all child tables (all rows) in the table
                for row in rows:
                    mycols = []
                    cols = row.find_elements(*loc_childtabledata)
                    for col in cols:
                        colvalue = col.text  # get all columns in child table row
                        mycols.append(colvalue)
                    file.writerow(mycols)
                f.write("==========================================================================================\n")
            with open(filenamestr) as f:
                print(f.read())
        except:
            print('List View not fetched')
            global exception_counter
            exception_counter = exception_counter + 1

    def getTable(self, filename, loc_table, loc_header, loc_parenttablerow, loc_parenttable, loc_allchildtable,
                 loc_childtabledata):
        try:
            filenamestr = str(filename)
            with open(filenamestr, 'a') as f:
                file = csv.writer(f)
                table = driver.find_element(*loc_table)
                header = table.find_elements(*loc_header)
                myheader = []
                for h in header:
                    header_text = h.text
                    myheader.append(header_text)
                file.writerow(myheader)
                f.write(
                    "============================================================================================\n")

                table_id = table.find_element(*loc_parenttable)
                rows = table_id.find_elements(*loc_allchildtable)  # get all child tables (all rows) in the table
                for row in rows:
                    mycols = []
                    cols = row.find_elements(*loc_childtabledata)
                    for col in cols:
                        colvalue = col.text  # get all columns in child table row
                        mycols.append(colvalue)
                    file.writerow(mycols)
                f.write("==========================================================================================\n")
            with open(filenamestr) as f:
                print(f.read())
        except:
            print('List View not fetched')
            global exception_counter
            exception_counter = exception_counter + 1

    def getAccountActivationEmail(self, EmailID):
        try:
            time.sleep(10)
            driver.get("http://www.yopmail.com/en/")
            time.sleep(4)
            inbox = driver.find_element_by_id('login')
            inbox.send_keys(EmailID)
            inbox.send_keys(Keys.ENTER)
            time.sleep(5)
            frame1 = driver.find_element_by_xpath("//iframe[@id='ifmail']")
            driver.switch_to.frame(frame1)
            driver.find_element_by_xpath("//div[@id='mailmillieu']/div[2]/a").click()
            WebDriverWait(driver, 20).until(EC.number_of_windows_to_be(2))
            child = driver.window_handles[1]
            driver.switch_to_window(child)


        except:
            print("Activation email not found")
            global exception_counter
            exception_counter = exception_counter + 1

    def switchToIframe(self, locator):
        try:

            frame_element = driver.find_element(*locator)
            print(locator)
            print(frame_element)
            driver.switch_to.frame(frame_element)
            print("after switch frame")
            time.sleep(8)

        except:
            print("Can't switch to iframe")
            global exception_counter
            exception_counter = exception_counter + 1

    def switchOutFromCurrentIframe(self):
        try:
            driver.switch_to.default_content()
            print("outside current iframe")
            time.sleep(5)

        except:
            print("Can't switch out of iframe")
            global exception_counter
            exception_counter = exception_counter + 1

    def enterRandomNumber(self, locator, digitCount):
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            start_range = int(digitCount) ** 1
            end_range = int(digitCount) ** 10
            random_number = random.randint(start_range, end_range)
            element.send_keys(random_number)
            time.sleep(5)
        except:
            print("Can't find specified element for entering randomNumber")
            global exception_counter
            exception_counter = exception_counter + 1


class ActionsInExcel:

    def logResultInFiles(self, filename, test_step, result):
        logstring = test_step + ":                     " + result
        CsvLogWriterObj.writeText(filename, logstring)

    def sendReport(self, toEmails, list_of_attachments, report_file_path):
        fromaddr = "testautomationt2b@gmail.com"
        toaddr = ','.join(toEmails)
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = "FleetLocate Smoke Testing at " + str(datetime.datetime.now().strftime("%d-%m-%y-%H-%M"))
        ListNames = "Summary of Sanity Testing:\r\n"
        body_reportfile = open(report_file_path, 'r')
        execution_report = []
        for line in body_reportfile:
            execution_report.append(line)
        lines = ' '.join(execution_report)

        body = ListNames + lines

        msg.attach(MIMEText(body, 'plain'))

        for n in range(0, len(list_of_attachments)):
            filename = list_of_attachments[n]
            attachment = open(list_of_attachments[n], "rb")

            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(fromaddr, "t2b@12345!")
        text = msg.as_string()
        server.sendmail(fromaddr, toEmails, text)
        server.quit()

    def actionOnLocator(self, locator_type, locator_value, action_name, *data):
        data_list = list(data)
        action_name = action_name.strip().upper()
        locator_type = locator_type.strip().upper()
        # Create object for DefineLocatorsBy
        DefineLocatorsByObj = DefineLocatorsBy()
        WebApplicationActionsObj = WebApplicationActions()

        if action_name == 'CLICK':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.clickElement(locator)

        elif action_name == 'FIRST_DROPDOWN_VALUE':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.expandEnterKeyOnAutoCompleteDropdown(locator)

        elif action_name == 'DOUBLECLICK':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.doubleclickElement(locator)

        elif action_name == 'ENTER':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.sendKeyENTER(locator, data_list[0])

        elif action_name == 'ENTER_KEY_DOWN':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.sendKeyDOWN(locator, data_list[0])

        elif action_name == 'ENTER_TEXT_SELECT_FIRST_DROPDOWN_OPTION':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.autoCompleteDropDownEnterTextFirstOption(locator, data_list[0])

        elif action_name == 'ENTER_TEXT_KEYDOWN_SELECT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.autoCompleteDropDownHidden(locator, data_list[0])

        elif action_name == 'DROPDOWN_MENU_OPTION':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.selectFromDropDownMenuOptions(locator, data_list[0])

        elif action_name == 'TAKE_SCREENSHOT':
            WebApplicationActionsObj.screenShot()

        elif action_name == 'ENTER_TEXT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.sendText(locator, data_list[0])


        elif action_name == 'GET_TOAST_TEXT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            toastinfo = WebApplicationActionsObj.getToastText(locator, data_list[0], data_list[1])
            global textholder
            textholder = toastinfo


        elif action_name == 'ENTER_TEXT_WITH_TIMESTAMP':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.sendTextWithTimeStamp(locator, data_list[0])

        elif action_name == 'ENTER_RANDOM_NUMBER':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.enterRandomNumber(locator, data_list[0])


        elif action_name == 'EDIT_TEXT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.clearText(locator)
            test_data = data_list[0]
            str_counter = str(varGlobalCounter)
            if '$VARCOUNTER$' in data_list[0]:
                test_data = test_data.replace('$VARCOUNTER$', str_counter)
                WebApplicationActionsObj.sendText(locator, test_data)
            else:
                WebApplicationActionsObj.sendText(locator, data_list[0])

        elif action_name == 'SWITCH_TO_ACTIVE_ELEMENT':
            WebApplicationActionsObj.switchToActiveElement()


        elif action_name == 'SWITCH_TO_ACTIVE_WINDOW':
            print("Current windows:", driver.window_handles)
            WebDriverWait(driver, 20).until(lambda driver: len(driver.window_handles) > 1)
            child = driver.window_handles[1]
            driver.switch_to.window(child)
            time.sleep(4)

        elif action_name == 'CLEAR_TEXT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.clearText(locator)


        elif action_name == 'ENTER_TEXT_KEYENTER':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.sendTextKeyENTER(locator, data_list[0])



        elif action_name == 'MENU_LOGOUT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.companyLogout(locator)

        elif action_name == 'SLEEP':
            WebApplicationActionsObj.addSleep(data_list[0])

        elif action_name == 'SET_CALENDAR_DATE':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.setCalendarDate(locator, data_list[0])

        elif action_name == 'GET_ATTRIBUTE':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            attribute_value = WebApplicationActionsObj.getAttribute(locator, data_list[0])
            CsvLogWriterObj.writeText(log_file_path, attribute_value)
            return (attribute_value)

        elif action_name == 'GET_ATTRIBUTE_IN_SVG':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            attribute_value = WebApplicationActionsObj.getAttributeFromSvg(locator, data_list[0])
            CsvLogWriterObj.writeText(log_file_path, attribute_value)
            return (attribute_value)


        elif action_name == 'GET_TEXT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            label_value = WebApplicationActionsObj.getText(locator)
            CsvLogWriterObj.writeText(log_file_path, label_value)
            return (label_value)


        elif action_name == 'SWITCH_TO_IFRAME':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.switchToIframe(locator)

        elif action_name == 'SWITCH_OUT_IFRAME':
            WebApplicationActionsObj.switchOutFromCurrentIframe()

        elif action_name == 'ACCEPT_JAVASCRIPT_ALERT':
            WebApplicationActionsObj.acceptAlert()

        elif action_name == 'CHECK_TEXT_IN_STRING':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            label_value = WebApplicationActionsObj.checkText(locator, data_list[0])
            CsvLogWriterObj.writeText(log_file_path, label_value)
            return (label_value)


        elif action_name == 'GET_INNERHTML_SAVE_IN_GLOBAL_DIC':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            label_value = WebApplicationActionsObj.getTextAndSaveInGlobalDic(locator, data_list[0])

        elif action_name == 'ACTION_ON_GLOBAL_DIC_VALUE':
            link = WebApplicationActionsObj.getValueFromGlobalDic(data_list[0])
            uncoded_link = html.unescape(link)
            WebApplicationActionsObj.openURL(uncoded_link)
            time.sleep(5)


        elif action_name == 'CLOSE_TOOLTIP':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.closeLearningTooltip(locator)

        elif action_name == 'POP_UP':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.checkPopup(locator)


        elif action_name == 'FILTER_DROPDOWN_LIST':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.filterValueFromDropDownList(locator, data_list[0])

        elif action_name == 'FILTER_ON_NTH_VALUE_FROM_DROPDOWN_LIST':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            listlocatorsxpath = ((locator_value.split("/button")[0]) + "/div/span/button[" + str(data_list[0]) + "]")
            nthlistlocator = DefineLocatorsByObj.locatorValue(locator_type, listlocatorsxpath)
            WebApplicationActionsObj.filterOnNthValueFromDropDownList(locator, nthlistlocator)


        elif action_name == 'FILTER_ON_NTH_VALUE':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            print(locator)
            listlocatorsxpath = ((locator_value.split("/p")[2]) + "select/option[" + str(data_list[0]) + "]")
            print(listlocatorsxpath)
            nthlistlocator = DefineLocatorsByObj.locatorValue(locator_type, listlocatorsxpath)
            WebApplicationActionsObj.filterOnNthValue(locator, nthlistlocator)


        elif action_name == 'SELECT_RADIO_FROM_LIST':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.selectRadioButtonFromList(locator, data_list[0])

        elif action_name == 'ENTER_VALUE_FROM_DROPDOWN_OPTIONS':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.enterValueDropDownOption(locator, data_list[0])

        elif action_name == 'DRAG_DROP':
            sourcelocator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            targetlocator = DefineLocatorsByObj.locatorValue(locator_type, data_list[1])
            WebApplicationActionsObj.drag_drop(sourcelocator, targetlocator)

        elif action_name == 'ENTER_VALUE_MULTI_SELECTION_FIRST_OPTION':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.autoCompleteDropdownMultipleSelectionFirstOption(locator)

        elif action_name == 'RECORDS_PER_PAGE':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            listlocatorsxpath = ((locator_value.split("/button")[0]) + "/div/button")
            listlocator = DefineLocatorsByObj.locatorValue(locator_type, listlocatorsxpath)
            WebApplicationActionsObj.filterValueFromDropDownList(locator, listlocator, data_list[0])

        elif action_name == 'CLICK_SECOND_COL_Nth_ROW':
            WebApplicationActionsObj.clickOnSecondColumnOfNthRow(data_list[0])


        elif action_name == 'CLICK_Nth_ROW':
            WebApplicationActionsObj.clickOnNthRow(data_list[0])

        elif action_name == 'WAIT_FOR_ELEMENT_CLICK':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            listview = WebApplicationActionsObj.waitForElementAndClick(locator, data_list[0])


        elif action_name == 'SEND_EMAIL':
            WebApplicationActionsObj.sendTestExecutionReport(data_list[0], log_file_path, report_file_path)

        elif action_name == 'LOG_IN_FILE':
            text = data_list[0]
            CsvLogWriterObj.writeText(log_file_path, text)

        elif action_name == 'OPEN_URL':
            WebApplicationActionsObj.openURL(data_list[0])

        elif action_name == 'SCROLL_TO_ELEMENT':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.scrollToElement(locator)

        elif action_name == 'SCROLL_DOWN':
            WebApplicationActionsObj.scrollDown()

        elif action_name == 'UPLOAD_FILE':
            locator = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            WebApplicationActionsObj.uploadFile(locator, data_list[0])

        elif action_name == 'GET_ACTIVATION_MAILINATOR_EMAIL':
            test_data = data_list[0]
            str_counter = str(varGlobalCounter)
            if '$VARCOUNTER$' in data_list[0]:
                test_data = test_data.replace('$VARCOUNTER$', str_counter)
            email_subject = "myEtimecard: Account Activation Details"
            WebApplicationActionsObj.getAccountActivationEmail(test_data)


        elif action_name == 'GET_LIST':
            loc_header = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(1, 2),
                                                          commonlocatorsdata.get_row_col(1, 3))
            loc_listname = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(2, 2),
                                                            commonlocatorsdata.get_row_col(2, 3))
            loc_parenttablerow = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(3, 2),
                                                                  commonlocatorsdata.get_row_col(3, 3))
            loc_parenttable = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(4, 2),
                                                               commonlocatorsdata.get_row_col(4, 3))
            loc_allchildtable = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(5, 2),
                                                                 commonlocatorsdata.get_row_col(5, 3))
            loc_childtabledata = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(6, 2),
                                                                  commonlocatorsdata.get_row_col(6, 3))
            list_data = WebApplicationActionsObj.getList(log_file_path, loc_header, loc_listname, loc_parenttablerow,
                                                         loc_parenttable, loc_allchildtable, loc_childtabledata)

        elif action_name == 'GET_TABLE':
            loc_header = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(1, 2),
                                                          commonlocatorsdata.get_row_col(1, 3))
            loc_parenttablerow = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(3, 2),
                                                                  commonlocatorsdata.get_row_col(3, 3))
            loc_parenttable = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(4, 2),
                                                               commonlocatorsdata.get_row_col(4, 3))
            loc_allchildtable = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(5, 2),
                                                                 commonlocatorsdata.get_row_col(5, 3))
            loc_childtabledata = DefineLocatorsByObj.locatorValue(commonlocatorsdata.get_row_col(6, 2),
                                                                  commonlocatorsdata.get_row_col(6, 3))
            loc_table = DefineLocatorsByObj.locatorValue(locator_type, locator_value)
            list_data = WebApplicationActionsObj.getTable(log_file_path, loc_table, loc_header, loc_parenttablerow,
                                                          loc_parenttable, loc_allchildtable, loc_childtabledata)

        else:
            print(f"Unknown action skipped: {action_name}")
            CsvLogWriterObj.writeText(log_file_path, f"Unknown action skipped: {action_name}")
            global exception_counter
            exception_counter += 1


filepaths = CsvFileReader("C:\\Python\\Python313\\Scripts\\SanityFilePaths.csv")
# driver = webdriver.Chrome(filepaths.get_row_col(0, 1))

commonlocatorsdata_file_path = filepaths.get_row_col(2, 1)
# READ LIST OF LOCATORS FILES
locators_files = filepaths.get_row_col(3, 1)
log_file_main_path = filepaths.get_row_col(1, 1)
locators_files_data = CsvFileReader(locators_files)
locators_files_count = sum(1 for line in open(locators_files))

# list_of_attachments = []

# Get counter value
counter_file = filepaths.get_row_col(4, 1)
counterdata = CsvFileReader(counter_file)
varGlobalCounter = counterdata.get_row_col(0, 0)

# Define remove file object
removeFileObj = RemoveFile()

# Get Screenshots folder
screenshots_file_path = filepaths.get_row_col(6, 1)

# RUN AUTOMATION SCRIPT FOR EACH LOCATOR FILE IN LIST OF LOCATORS FILE
for i in range(1, locators_files_count):
    locator_file_run = locators_files_data.get_row_col(i, 5)
    str_locator_fine_run = str(locator_file_run)
    if str_locator_fine_run == 'YES':
        exception_counter = 0
        locator_file_name = locators_files_data.get_row_col(i, 0)
        locator_file_main_path = filepaths.get_row_col(5, 1)
        complete_locator_file_path = locator_file_main_path + locator_file_name + '.csv'
        pagelocatorsdata_file_path = complete_locator_file_path

        common_log_file_path = filepaths.get_row_col(2, 1)
        log_file_path = log_file_main_path + locator_file_name + datetime.datetime.now().strftime(
            '%H_%M%p%B%d') + '.csv'

        # READ INDIVIDUAL LOCATOR FILE
        pagelocatorsdata = CsvFileReader(pagelocatorsdata_file_path)
        commonlocatorsdata = CsvFileReader(commonlocatorsdata_file_path)
        # Define objects of CSV write classes for Email attachment log file, Report File, Counter File
        CsvFileWriterObj = Litmus_Common_Functions.CsvFileWriter()
        CsvLogWriterObj = CsvLogWriter()
        CsvCounterWriterObj = CsvLogWriter()

        CsvLogWriterObj.writeText(log_file_path, "DETAILS OF EXECUTION RESULTS")

        # Define objects of Actions in Excel class
        ActionsInExcelObj = ActionsInExcel()

        # RESETTING RESULTS TO NOT EXECUTED
        CsvFileWriterObj.write_row_col(locators_files, i, 2, "NOT EXECUTED YET")
        CsvFileWriterObj.write_row_col(locators_files, i, 3, "NOT EXECUTED YET")
        CsvFileWriterObj.write_row_col(locators_files, i, 4, "NOT EXECUTED YET")

        config = Options()
        # driver = webdriver.Chrome(ChromeDriverManager().install(), options=config)
        # driver = webdriver.Chrome('C:\\chromedriver.exe')
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.get(locators_files_data.get_row_col(i, 1))
        driver.maximize_window()
        time.sleep(2)

        global screenShot


        def screenShot():
            screenshotfilename = datetime.datetime.now().strftime('%H_%M%p%B%d') + '.png'
            driver.save_screenshot(screenshots_file_path + '\\' + screenshotfilename)
            time.sleep(4)


        # FOR EACH TEST STEP IN INDIVIDUAL LOCATOR FILE
        row_count = sum(1 for line in open(pagelocatorsdata_file_path))
        for n in range(1, row_count):
            cell_test_step = pagelocatorsdata.get_row_col(n, 0)
            str_test_step = str(cell_test_step)
            if "TEST DATA" == str_test_step:
                CsvLogWriterObj.writeText(log_file_path, "Test Data is:")
                cell_data = pagelocatorsdata.get_row_col(n, 5)
                if '$VARCOUNTER$' in cell_data:
                    str_counter = str(varGlobalCounter)
                    test_data = cell_data.replace('$VARCOUNTER$', str_counter)
                    CsvLogWriterObj.writeText(log_file_path, test_data)
                else:
                    CsvLogWriterObj.writeText(log_file_path, cell_data)

            if '#' not in str_test_step:
                cell_type = pagelocatorsdata.get_row_col(n, 2)
                cell_value = pagelocatorsdata.get_row_col(n, 3)
                cell_action = pagelocatorsdata.get_row_col(n, 4)
                cell_data = pagelocatorsdata.get_row_col(n, 5)
                cell_run = pagelocatorsdata.get_row_col(n, 6)
                cell_date2 = pagelocatorsdata.get_row_col(n, 7)
                if cell_run == 'Y':
                    before_action_exception_counter = exception_counter
                    ActionsInExcelObj.actionOnLocator(cell_type, cell_value, cell_action, cell_data, cell_date2)
                    after_action_exception_counter = exception_counter
                    execution_time = "Executed@" + datetime.datetime.now().strftime('%H_%M%p%B%d')
                    CsvFileWriterObj.write_row_col(pagelocatorsdata_file_path, n, 7, execution_time)
                    if before_action_exception_counter == after_action_exception_counter:
                        ActionsInExcelObj.logResultInFiles(log_file_path, cell_test_step, "Passed")
                    elif before_action_exception_counter != after_action_exception_counter:
                        ActionsInExcelObj.logResultInFiles(log_file_path, cell_test_step, "Failed")
                        CsvFileWriterObj.write_row_col(locators_files, i, 4, "FAILED")
        after_all_steps_execution_counter = exception_counter
        print(after_all_steps_execution_counter)
        execution_time = "Executed@" + datetime.datetime.now().strftime('%H_%M%p%B%d')

        # WRITING IN LIST OF LOCATORS FILES IF ALL PASSED
        CsvFileWriterObj.write_row_col(locators_files, i, 2, execution_time)
        CsvFileWriterObj.write_row_col(locators_files, i, 3, after_all_steps_execution_counter)
        if after_all_steps_execution_counter == 0:
            CsvFileWriterObj.write_row_col(locators_files, i, 4, "ALL PASS")
        # LIST OF ATTACHMENTS OF ALL RESULTS
        # list_of_attachments.append(log_file_path)
        # driver.close()
        # driver.quit()

# varGlobalCounternew = int(varGlobalCounter) + 1
# removeFileObj.removeFile(counter_file)
# lognewcounter = str(varGlobalCounternew)
# CsvCounterWriterObj.writeText(counter_file, lognewcounter)


# to_Emails = ['shubha.shukla@thoughts2binary.com']

# ActionsInExcelObj.sendReport(to_Emails, list_of_attachments, locators_files)