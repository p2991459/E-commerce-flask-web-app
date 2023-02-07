from queue import Queue
from project.main import create_app
from decouple import config
from airtable import airtable
from project.models import ArrangementTypesRecipe, FlowerProperties, Storage
from . import db
import time
from threading import Thread, current_thread


AIS_BASE_ID = config('AIS_BASE_ID')
AIS_API_KEY = config('AIS_API_KEY')
AIS_FLOWER_PROP_TABLE_ID = config('AIS_FLOWER_PROP_TABLE_ID')
AIS_ARRANGE_TYPES_TABLE_ID = config('AIS_ARRANGE_TYPES_TABLE_ID')
AIS_HARVEST_GOAL_TABLE_ID = config('AIS_HARVEST_GOAL_TABLE_ID')
AIS_ARR_PROD_TABLE_ID = config('AIS_ARR_PROD_TABLE_ID')
AIS_IN_STORAGE_TABLE_ID = config('AIS_IN_STORAGE_TABLE_ID')

def sync_airtable_data():
    print("===================================================================")
    print("Starting syncing airtable data")
    print("===================================================================")
    st = time.time()
    
    airtable_base = airtable.Airtable(AIS_BASE_ID, AIS_API_KEY)
    app = create_app()
    q = Queue()
    
    thread1 = Thread(target=sync_flower_properties, args=(q, airtable_base, app), name='Thread-1')
    print("Starting Thread 1")
    thread1.start()
    thread2 = Thread(target=sync_arrangement_types_recipe, args=(q, airtable_base, app), name='Thread-2')
    print("Starting Thread 2")
    thread2.start()
    thread3 = Thread(target=syn_storage_details, args=(q,airtable_base, app), name='Thread-3')
    print("Starting Thread 3")
    thread3.start()

    thread1.join()
    thread2.join()
    thread3.join()
    
    # All thread fetch data and put object in the Queue, now consuming queue store all the object in the database.
    print("Size of the Q is : ", q.qsize())
    try:
        while not q.empty():
            db.session.add(q.get())
        db.session.commit()
    except Exception as e:
        print("Error in database operation.", str(e))
    q.join()
    
    et = time.time()
    print("===================================================================")
    print("Execution time for synching airtable data: ", (et - st), " seconds.")
    print("===================================================================")
    
    
def sync_flower_properties(q, airtable_base, app):
    print(current_thread().name, "Starting syncing of Flower Properties.")
    st = time.time()
    response = airtable_base.iterate(AIS_FLOWER_PROP_TABLE_ID)
    for record in response:
        id = record['id']
        fields = record['fields']
        flower_property = None
        # Need to set app context for fetching data from the database
        with app.app_context():
            flower_property = FlowerProperties.query.get(id)
            if not flower_property:
                flower_property = FlowerProperties()
                flower_property.id = id
        print(current_thread().name, "Name of Flower Properties : ", fields['Name'] if 'Name' in fields else '')
        flower_property.name = fields['Name'] if 'Name' in fields else ''
        flower_property.source = ','.join(fields['Source']) if 'Source' in fields else ''
        flower_property.storage_type = fields['Storage type'] if 'Storage type' in fields else ''
        flower_property.flower_type = ','.join(fields['Flower Type']) if 'Flower Type' in fields else ''
        flower_property.time_to_expire = fields['Time to Expire'] if 'Time to Expire' in fields else '0'
        flower_property.in_storage = get_storage_detail(fields['In Storage 2'], airtable_base) if 'In Storage 2' in fields else ''
        
        flower_property.arr_type_recipe1 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 1'], airtable_base) if 'Arrangement Types Recipe 1' in fields else ''
        flower_property.arr_type_recipe2 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 2'], airtable_base) if 'Arrangement Types Recipe 2' in fields else ''
        flower_property.arr_type_recipe3 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 3'], airtable_base) if 'Arrangement Types Recipe 3' in fields else ''
        flower_property.arr_type_recipe4 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 4'], airtable_base) if 'Arrangement Types Recipe 4' in fields else ''
        flower_property.arr_type_recipe5 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 5'], airtable_base) if 'Arrangement Types Recipe 5' in fields else ''
        flower_property.arr_type_recipe6 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 6'], airtable_base) if 'Arrangement Types Recipe 6' in fields else ''
        flower_property.arr_type_recipe7 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 7'], airtable_base) if 'Arrangement Types Recipe 7' in fields else ''
        flower_property.arr_type_recipe8 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 8'], airtable_base) if 'Arrangement Types Recipe 8' in fields else ''
        flower_property.arr_type_recipe9 = get_arrangement_type_recipe(fields['Arrangement Types Recipe 9'], airtable_base) if 'Arrangement Types Recipe 9' in fields else ''
        q.put(flower_property)
        q.task_done()
        
    et = time.time()
    elapsed_time = et - st
    print(current_thread().name, "End syncing of Flower Properties")
    print("=================================================================================================")
    print(current_thread().name, "Execution time for synching flower properties: ", elapsed_time, " seconds.")
    print("=================================================================================================")
    

def get_arrangement_type_recipe(ids, airtable_base):
    if len(ids) > 0:
        recipe_names = []
        for id in ids:
            response = airtable_base.get(table_name="Arrangement Types Recipe", record_id=id)
            if 'Name' in response['fields']:
                recipe_names.append(response['fields']['Name'])
        arrangement_types_recipes_name = ', '.join(recipe_names)
        print(current_thread().name, "Recipes Name ", arrangement_types_recipes_name)
        return arrangement_types_recipes_name
    else:
        return ''


def get_storage_detail(ids, airtable_base):
    if len(ids) > 0:
        storage_details = []
        for id in ids:
            response = airtable_base.get(table_name="Arrangement Types Recipe", record_id=id)
            if 'Name' in response['fields']:
                storage_details.append(response['fields']['Name'])
        storage_name = ', '.join(storage_details)
        print(current_thread().name, "Storage Details ", storage_name)
        return storage_name
    else:
        return ''


def sync_arrangement_types_recipe(q, airtable_base, app):
    print(current_thread().name, "Starting syncing of Arrangement Types Recipe")
    st = time.time()
    response = airtable_base.iterate(AIS_ARRANGE_TYPES_TABLE_ID)
    for record in response:
        id = record['id']
        fields = record['fields']
        arr_type_recipe = None
        # Need to set app context for fetching data from the database
        with app.app_context():
            arr_type_recipe = ArrangementTypesRecipe.query.get(id)
            if not arr_type_recipe:
                arr_type_recipe = ArrangementTypesRecipe()
                arr_type_recipe.id = id
        
        print(current_thread().name, "Name of Arrangement Types Recipe : ", fields['Name'] if 'Name' in fields else '')
        arr_type_recipe.name = fields['Name'] if 'Name' in fields else ''
        arr_type_recipe.flower1 = get_flower_property_detail(fields['Flower 1'], airtable_base) if 'Flower 1' in fields else ''
        arr_type_recipe.qty_flower1 = fields['# of Flower 1'] if '# of Flower 1' in fields else ''
        arr_type_recipe.flower2 = get_flower_property_detail(fields['Flower 2'], airtable_base) if 'Flower 2' in fields else ''
        arr_type_recipe.qty_flower2 = fields['# of Flower 2'] if '# of Flower 2' in fields else ''
        arr_type_recipe.flower3 = get_flower_property_detail(fields['Flower 3'], airtable_base) if 'Flower 3' in fields else ''
        arr_type_recipe.qty_flower3 = fields['# of Flower 3'] if '# of Flower 3' in fields else ''
        arr_type_recipe.flower4 = get_flower_property_detail(fields['Flower 4'], airtable_base) if 'Flower 4' in fields else ''
        arr_type_recipe.qty_flower4 = fields['# of Flower 4'] if '# of Flower 4' in fields else ''
        arr_type_recipe.flower5 = get_flower_property_detail(fields['Flower 5'], airtable_base) if 'Flower 5' in fields else ''
        arr_type_recipe.qty_flower5 = fields['# of Flower 5'] if '# of Flower 5' in fields else ''
        arr_type_recipe.flower6 = get_flower_property_detail(fields['Flower 6'], airtable_base) if 'Flower 6' in fields else ''
        arr_type_recipe.qty_flower6 = fields['# of Flower 6'] if '# of Flower 6' in fields else ''
        arr_type_recipe.flower7 = get_flower_property_detail(fields['Flower 7'], airtable_base) if 'Flower 7' in fields else ''
        arr_type_recipe.qty_flower7 = fields['# of Flower 7'] if '# of Flower 7' in fields else ''
        arr_type_recipe.flower8 = get_flower_property_detail(fields['Flower 8'], airtable_base) if 'Flower 8' in fields else ''
        arr_type_recipe.qty_flower8 = fields['# of Flower 8'] if '# of Flower 8' in fields else ''
        arr_type_recipe.flower9 = get_flower_property_detail(fields['Flower 9'], airtable_base) if 'Flower 9' in fields else ''
        arr_type_recipe.qty_flower9 = fields['# of Flower 9'] if '# of Flower 9' in fields else ''
        arr_type_recipe.arr_production = get_arrangement_production_detail(fields['Arrangement Production'], airtable_base) if 'Arrangement Production' in fields else ''
        arr_type_recipe.harvest_goal = get_harvest_goal_detail(fields['Harvest Goals'], airtable_base) if 'Harvest Goals' in fields else ''
        q.put(arr_type_recipe)
        q.task_done()
        
    et = time.time()
    elapsed_time = et - st
    print(current_thread().name, "End syncing of Arrangement Types Recipe")
    print("=================================================================================================")
    print(current_thread().name, "Execution time for synching arrangment types recipe: ", elapsed_time, " seconds.")
    print("=================================================================================================")


def get_flower_property_detail(ids, airtable_base):
    if len(ids) > 0:
        flower_properties = []
        for id in ids:
            response = airtable_base.get(AIS_FLOWER_PROP_TABLE_ID, record_id=id, fields=['Name'])
            if 'Name' in response['fields']:
                flower_properties.append(response['fields']['Name'])
        flower_properties_name = ', '.join(flower_properties)
        print(current_thread().name, "Flower Properties Name ", flower_properties_name)
        return flower_properties_name
    else:
        return ''


def get_harvest_goal_detail(ids, airtable_base):
    if len(ids) > 0:
        harvest_goal = []
        for id in ids:
            response = airtable_base.get(AIS_HARVEST_GOAL_TABLE_ID, record_id=id, fields=['Name'])
            if 'Name' in response['fields']:
                harvest_goal.append(response['fields']['Name'])
        harvest_goal_name = ', '.join(harvest_goal)
        print(current_thread().name, "Harvest Goal Name ", harvest_goal_name)
        return harvest_goal_name
    else:
        return ''


def get_arrangement_production_detail(ids, airtable_base):
    if len(ids) > 0:
        arr_prod = []
        for id in ids:
            response = airtable_base.get(AIS_ARR_PROD_TABLE_ID, record_id=id, fields=['Name'])
            if 'Name' in response['fields']:
                arr_prod.append(response['fields']['Name'])
        arr_prod_name = ', '.join(arr_prod)
        print(current_thread().name, "Arrange Prod. Name ", arr_prod_name)
        return arr_prod_name
    else:
        return ''


def syn_storage_details(q, airtable_base, app):
    print(current_thread().name, "Starting syncing of Flower Storage Details")
    st = time.time()
    response = airtable_base.iterate(AIS_IN_STORAGE_TABLE_ID)
    for record in response:
        id = record['id']
        fields = record['fields']
        storage = None
        # Need to set app context for fetching data from the database
        with app.app_context():
            storage = Storage.query.get(id)
            if not storage:
                storage = Storage()
                storage.id = id
        
        print(current_thread().name, "Name of Storage Record : ", fields['Name'] if 'Name' in fields else '')
        id = record['id']
        response_fields = record['fields']
        name = response_fields['Name'] if 'Name' in response_fields else ''
        with app.app_context():
            flower_name = get_flower_property_detail(response_fields['flower Name'], airtable_base) if 'flower Name' in response_fields else ''
        amt_harvested = response_fields['Amount Harvested'] if 'Amount Harvested' in response_fields else ''
        amt_in_storage = response_fields['Amount in storage'] if 'Amount in storage' in response_fields else ''
        harvest_date = response_fields['Harvest Date'] if 'Harvest Date' in response_fields else ''
        exp_tag = response_fields['Expiration Tag'] if 'Expiration Tag' in response_fields else ''
        exp_date = response_fields['Expiration Date'] if 'Expiration Date' in response_fields else ''
        harvest_date = response_fields['Harvest Date'] if 'Harvest Date' in response_fields else ''
        flower_type = ','.join(response_fields['Flower Type (from flower Name)']) if 'Flower Type (from flower Name)' in response_fields else ''
        time_to_expire = response_fields['Time to Expire ( Flower Properties)'] if 'Time to Expire ( Flower Properties)' in response_fields else ''
        harvest_goals = get_harvest_goal_detail(response_fields['Harvest Goals'], airtable_base) if 'Harvest Goals' in response_fields else ''
        harvest_goals2 = get_harvest_goal_detail(response_fields['Harvest Goals 2'], airtable_base) if 'Harvest Goals 2' in response_fields else ''
        decrease1 = response_fields['Decrease 1'] if 'Decrease 1' in response_fields else ''
        decrease2 = response_fields['Decrease 2'] if 'Decrease 2' in response_fields else ''
        decrease3 = response_fields['Decrease 3'] if 'Decrease 3' in response_fields else ''
        decrease4 = response_fields['Decrease 4'] if 'Decrease 4' in response_fields else ''
        decrease5 = response_fields['Decrease 5'] if 'Decrease 5' in response_fields else ''
        decrease6 = response_fields['Decrease 6'] if 'Decrease 6' in response_fields else ''
        amt_in_storage1 = response_fields['Amount in Storage 1'] if 'Amount in Storage 1' in response_fields else ''
        amt_in_storage2 = response_fields['Amount in Storage 2'] if 'Amount in Storage 2' in response_fields else ''
        amt_in_storage3 = response_fields['Amount in Storage 3'] if 'Amount in Storage 3' in response_fields else ''
        amt_in_storage4 = response_fields['Amount in Storage 4'] if 'Amount in Storage 4' in response_fields else ''
        amt_in_storage5 = response_fields['Amount in Storage 5'] if 'Amount in Storage 5' in response_fields else ''
        amt_in_storage6 = response_fields['Amount in Storage 6'] if 'Amount in Storage 6' in response_fields else ''
        storage.name = name
        storage.flower_name = flower_name
        storage.amt_in_storage = amt_in_storage
        storage.amt_harvested = amt_harvested
        storage.exp_tag = exp_tag
        storage.exp_date = exp_date
        storage.harvest_date = harvest_date
        storage.flower_type = flower_type
        storage.time_to_expire = time_to_expire
        storage.amt_in_storage1 = amt_in_storage1
        storage.amt_in_storage2 = amt_in_storage2
        storage.amt_in_storage3 = amt_in_storage3
        storage.amt_in_storage4 = amt_in_storage4
        storage.amt_in_storage5 = amt_in_storage5
        storage.amt_in_storage6 = amt_in_storage6
        storage.decrease1 = decrease1
        storage.decrease2 = decrease2
        storage.decrease3 = decrease3
        storage.decrease4 = decrease4
        storage.decrease5 = decrease5
        storage.decrease6 = decrease6
        storage.harvest_goal = harvest_goals
        storage.harvest_goal2 = harvest_goals2
        q.put(storage)
        q.task_done()
        
    et = time.time()
    elapsed_time = et - st
    print(current_thread().name, "End syncing of Flower Storage Details")
    print("=================================================================================================")
    print(current_thread().name, "Execution time for synching Flower Storage Details: ", elapsed_time, " seconds.")
    print("=================================================================================================")