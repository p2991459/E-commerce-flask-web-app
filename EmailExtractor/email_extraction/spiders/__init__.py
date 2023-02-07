# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

import time
import sqlite3
import os
import pandas as pd


def post_scrap(output, name):
    print('Spider closed, Writing to DB.')
    try:
        conn = sqlite3.connect("../project/db.sqlite")
        cursor = conn.cursor()

        dt_time = time.strftime('%Y-%m-%d %H:%M:%S')

        # to get total count
        # total_emails = len(pd.read_csv(output))

        # to get input id
        row = cursor.execute('select id from crawler_input where source = "%s"' % name).fetchone()
        if len(row):
            input_id = row[0]
        else:
            query = '''insert into crawler_input (source) values ("%s")''' % name
            cursor.execute(query)
            conn.commit()
            input_id = cursor.lastrowid

        # writing crawler_output table
        query = '''insert into crawler_output 
            (output_file, crawled_datetime, crawler_input_id, total_emails_found)
            values ("%s", "%s", "%s", "%s")''' % (output, dt_time, input_id, total_emails)
        conn.execute(query)
        conn.commit()

        # csv-to-db
        os.system('flask main csv-to-db --file-name=email-scrapper/%s' % output)
    except Exception as e:
        print(e)
