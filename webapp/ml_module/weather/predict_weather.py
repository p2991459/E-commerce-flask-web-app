# -*- coding: utf-8 -*-
"""
    Weather Prediction
    ~~~~~~~~~~~~~~~~

    Implementation of Weather Prediction


    >>  We have covered following columns as result:
            1. Minimum Temperature (°C)
            2. Maximum Temperature (°C)
            3. Perception Rate (MM)
    
    >>  Functionalities:
            1. Fetch dataset based on zip code
            2. Predict & save data based on given dataset(.csv)

"""

import os
import pandas as pd
from datetime import date, timedelta


def fetch_dataset(zipcode, data_dir, api_key):
    from wwo_hist import retrieve_hist_data
    try:
        os.chdir(data_dir)
    except FileNotFoundError as e:
        print(e)
        print('Creating dir...')
        os.makedirs(data_dir, exist_ok=True)
        os.chdir(data_dir)

    frequency=24

    yesterday = date.today() - timedelta(days = 1)
    end_date = yesterday
    start_date = '01-Jan-2009'
    api_key = api_key
    location_list = [zipcode]
    try:
        hist_weather_data = retrieve_hist_data(api_key,
                                location_list,
                                start_date,
                                end_date,
                                frequency,
                                location_label = False,
                                export_csv = True,
                                store_df = True)

    except Exception as e:
        print(e)



def predict_one_year_weather(zipcode, data_dir):
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_squared_error

    weather = pd.read_csv(data_dir + "/" + zipcode + ".csv",parse_dates=['date_time'])

    predictors = [
        "precipMM",
        "maxtempC", 
        "mintempC"
    ]

    # Generating next 1 year data based on mean value
    last_date_from_dataset = weather.iloc[-1].date_time
    generated_start_date = last_date_from_dataset + timedelta(days=1)    
    generated_end_date = generated_start_date.replace(year=generated_start_date.year + 1)
    future_date_range = pd.date_range(start=generated_start_date, end=generated_end_date, freq='D')

    mean_of_complete_year = pd.DataFrame({ 'date_time':future_date_range}, index=future_date_range.dayofyear)
    for col in predictors:
        mean_of_complete_year[col] = weather[col].groupby(weather['date_time'].dt.dayofyear).mean()
       
    mean_of_complete_year.sort_values('date_time', inplace=True)
    mean_of_complete_year['date_time'] = mean_of_complete_year['date_time'].dt.date

    # merging future data with existing
    weather = pd.concat([weather, mean_of_complete_year])
    weather.set_index("date_time", inplace=True)

    core_weather = weather[predictors].copy()

    core_weather.index = pd.to_datetime(core_weather.index)
    core_weather = core_weather.iloc[:-1,:].copy()
    core_weather.dropna(inplace=True)
    
    reg = Ridge(alpha=.1)
    def create_predictions(predictors, core_weather, reg):
        predicted_df = pd.DataFrame()
        target_columns = ['precipMM', 'maxtempC', 'mintempC']
        for target in target_columns:
            core_weather["monthly_avg"] = core_weather[target].groupby(core_weather.index.month).apply(lambda x: x.expanding(1).mean())
            core_weather["day_of_year_avg"] = core_weather[target].groupby(core_weather.index.dayofyear).apply(lambda x: x.expanding(1).mean())
            
            train = core_weather.loc[:last_date_from_dataset]
            test = core_weather.loc[generated_start_date.date():]

            reg.fit(train[predictors], train[target])
            predictions = reg.predict(test[predictors])
            
            error = mean_squared_error(test[target], predictions)
            print(target, 'error: ' , error)
            
            predicted_df[target] = pd.Series(predictions, index=test.index)
            core_weather.drop(['monthly_avg', 'day_of_year_avg'], axis=1, inplace=True)
        return predicted_df

    predicted_data = create_predictions(predictors, core_weather, reg)
    pd.set_option('display.max_rows', None)
    predicted_data.sort_index(inplace=True)
    return predicted_data

# for zipc in ['60621', '60637', '60615', '60624', '60608']:
#     predict_one_year_weather(zipc, data_dir)
#     print('=================================================')
#     break

