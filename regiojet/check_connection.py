#!/usr/bin/env python

import os
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DRIVER_PATH = os.path.join(SCRIPT_DIR, '..', 'phantomjs-2.1.1-linux-x86_64/bin')
# DRIVER_PATH = os.path.join(SCRIPT_DIR, '..')
os.environ['PATH'] += os.pathsep + DRIVER_PATH

import sys
sys.path.append(os.path.join(SCRIPT_DIR, '..'))

import time
import re
import logging
from selenium import webdriver
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from secret import credentials

PLACES = {
    'Brno': 10204002,
    'Vienna': 10202052,
    'Mikulas': 10202036,
}
QUERY = 'https://jizdenky.regiojet.cz/Booking/from/{}/to/{}/tarif/REGULAR/departure/{}'
TIMEOUT = 5
TEXTFILE = os.path.join(SCRIPT_DIR, 'email.txt')


class Connection(object):
    # def __init__(self, p_dep, t_dep, p_arr, t_arr, spaces):
    #     self.p_dep = p_dep
    #     self.t_dep = t_dep
    #     self.p_arr = p_arr
    #     self.t_arr = t_arr
    #     self.spaces = spaces

    def __init__(self, e, p_dep=None, p_arr=None, date=None):
        self.p_dep = p_dep
        self.t_dep = e.find('div', {'class': 'col_depart'}).text
        self.p_arr = p_arr
        self.t_arr = e.find('div', {'class': 'col_arival'}).text
        self.date = date
        self.spaces = int(e.find('div', {'class': 'col_space'}).text.strip())

    def __repr__(self):
        return '{} {} - {} {} free: {}'.format(
            self.p_dep, self.t_dep,
            self.t_arr, self.p_arr,
            self.spaces)

    def __str__(self):
        return '{} {} - {} {} free: {}'.format(
            self.p_dep, self.t_dep,
            self.t_arr, self.p_arr,
            self.spaces)


def check(driver, dep, arr, d, t=None):
    d = time.strptime(d, '%d.%m.%Y')
    dep = dep.capitalize()
    arr = arr.capitalize()
    driver.get(QUERY.format(PLACES[dep], PLACES[arr],
                            time.strftime('%Y%m%d', d)))
    time.sleep(TIMEOUT)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    lst = soup.find('div', {'id': 'ticket_lists'})

    if lst is None:
        return

    if t is not None:
        t = time.strptime(t, '%H:%M')
        gmt = time.localtime(time.mktime(t) + time.altzone)
    pattern = re.compile(r'^{}{}.*'.format(time.strftime('%Y%m%d', d), '' if t is None else time.strftime('%H%M', gmt)))
    elems = lst.find_all('div', {'class': 'routeSummary', 'ybus:rowid': pattern})
    return [Connection(e, dep, arr, d) for e in elems]


def send_email(c,
               address_from=credentials.GMAIL_ADDRESS,
               address_to=credentials.GMAIL_ADDRESS,
               login=credentials.GMAIL_LOGIN,
               password=credentials.GMAIL_PASSWORD):

    html = '<html><head></head><body>Book <a href="{}">here</a></body></html>'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = str(c)
    msg['From'] = address_from
    msg['To'] = address_to
    msg.attach(MIMEText(html.format(QUERY.format(PLACES[c.p_dep], PLACES[c.p_arr], time.strftime('%Y%m%d', c.date))), 'html'))

    s = smtplib.SMTP('smtp.gmail.com:587')
    s.ehlo()
    s.starttls()
    s.login(login, password)
    s.send_message(msg)
    s.quit()


def main(argv):

    if len(argv) < 4:
        print('usage ./{} dep arr d.m.Y [H:M]'.format(os.path.basename(sys.argv[0])))
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    driver = webdriver.PhantomJS()
    logging.info('Webdriver {} initialized.'.format(driver.name))
    # driver = webdriver.Firefox()
    cs_p = check(driver, *argv[1:])
    while True:
        cs = check(driver, *argv[1:])
        logging.info('\n{}'.format('\n'.join(str(c) for c in cs)))
        if cs is not None and len(cs) == len(cs_p):
            for c, c_p in zip(cs, cs_p):
                if c_p.spaces == 0 and c.spaces > 0:
                    send_email(c)
            time.sleep(60)
        cs_p = cs


if __name__ == '__main__':
    main(sys.argv)
