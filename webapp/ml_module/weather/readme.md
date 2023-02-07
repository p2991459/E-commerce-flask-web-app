Weather prediction :

	1. Fetching history weather data based on zipcode from worldweatheronline.com with help of wwo-hist python package.
		:~# flask main fetch-history-weather-data <optional: api_key>

		Note: optional api-key can be used from worldweatheronline.com in case existing one exceed the limit or any kind of authentication error

	2. Generating prediction for next one year, Date range would be from the next day of the dataset last date to the next year. It automatically insert newly generated data into Database and remove previously stored data for the same. 
		:~# flask main generate-weather-prediction

		Note: We are using following 3 values to predict:
			a. Minimum Temperature (°C)
            b. Maximum Temperature (°C)
            c. Perception Rate (MM)