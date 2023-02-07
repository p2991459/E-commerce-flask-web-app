def utility_processor():
    def get_stop_address(stops_list, stop_id):
        if stops_list:
            for stop in stops_list.keys():
                if stop == stop_id:
                    return '%s -- %s' % (
                        stops_list[stop]['name'],
                        stops_list[stop]['location']['address']
                    )
        return "NA"

    def get_driver_name(drivers_dict, driver_id):
        print("************")
        print(drivers_dict)
        print("------------")

        if drivers_dict:
            for driver in drivers_dict.keys():
                if driver == driver_id:
                    return drivers_dict[driver]['name']
        return driver_id

    return dict(get_driver_name=get_driver_name,
                get_stop_address=get_stop_address)
