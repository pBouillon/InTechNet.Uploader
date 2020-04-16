from configparser import ConfigParser
import click
from pathlib import Path
import psycopg2
from typing import List
import yaml

from utils.dataclasses import Module, Resource


def extract_config(filename='database.ini', section='postgresql'):
    '''Extract all configuration information'''
    # From: https://www.postgresqltutorial.com/postgresql-python/connect/
    # Create a parser
    parser = ConfigParser()
    
    # Read config file
    parser.read(filename)

    # Get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(
            'Section {0} not found in the {1} file'.format(section, filename))

    return db


def get_resources(path: Path) -> List[Resource]:
    '''Retrieve all html resources inside the module folder'''
    resources: List[Path] = path.glob('*.html')
    return [
        Resource(
            content=resource.read_text(encoding='utf8'),
            name=resource.name)
        for resource in resources]


def get_linked_resources(resources: List[Resource]) -> Resource:
    '''Link all provided resource by alphabetical order'''
    
    def link_resource_to_next(to_link: List[Resource]):
        '''Recursively link each resource to the next one'''
        if len(to_link) == 1:
            return
        
        to_link[0].next_resource = to_link[1]
        link_resource_to_next(to_link[1:])
    
    # Order resources by name
    resources.sort(key=lambda resource: resource.name)
    
    # Link each resource
    link_resource_to_next(resources)

    # Return the head of the linked resources
    return resources[0]


def get_module(module: Path) -> Module:
    '''Get module meta data'''
    # Get all YAML files
    module_conf_files = [
        file 
        for file in module.glob('**/*')
        if file.is_file() and file.suffix in ['.yml', '.yaml']]
    
    # Assert there is only a unique YAML file for the current module
    if len(module_conf_files) < 1:
        raise FileNotFoundError('No module yaml configuration file found')
    
    if len(module_conf_files) > 1:
        raise FileNotFoundError('Multiple yaml configuration files found for this module')

    return get_module_data(module_conf_files[0])


def get_module_data(module_file: Path) -> Module:
    '''Extract module data from its configuration file'''
    # Extract file data
    data = yaml.safe_load(module_file.read_text(encoding='utf8'))
    
    # Assert that each property is present
    if 'module' not in data.keys():
        raise KeyError('Field "module" missing in the module configuration file')
    
    if not all(key in ('name', 'description') for key in data['module']):
        raise KeyError(
            'Unable to read "name" and "description" properties of the module'
            '(are the keys missing ?)')
    
    return Module(**data['module'])


def record_module(module: Module, subscription_plan_id: int, config: dict = extract_config()):
    '''Record the provided module in database'''
    
    sql = '''
       INSERT INTO "module" ("ModuleDescription", "SubscriptionPlanId", "ModuleName")
       VALUES(%s, %s, %s);
    '''
    
    # From: https://www.postgresqltutorial.com/postgresql-python/insert/
    conn = None
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**config)
        # Create a new cursor
        cur = conn.cursor()
        # Execute the INSERT statement
        cur.execute(sql, (module.description, subscription_plan_id, module.name))
        # Commit the changes to the database
        conn.commit()
        # Close communication with the database
        cur.close()
    finally:
        if conn is not None:
            conn.close()

@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option(
    '--module',
    '-m',
    'module',
    help='Path to the module description file',
    type=click.Path(exists=True))
@click.option(
    '--subscriptionplan',
    '-s',
    'subscription_plan_id',
    default=1,
    help='Id of the subscription plan to which this module is intended',
    type=int)
def upload(path, module, subscription_plan_id):
    '''Upload a module and its resources in the correct order'''
    root_path = Path(path)
    
    # Retrieve all resources
    resources: List[Path] = get_resources(root_path)
    
    # Sort and link them
    resources_head = get_linked_resources(resources)

    # Retrieve module meta data
    module_path = Path(module if module else path)
    module = get_module(module_path)
    
    # Bind the first resource to the module
    module.first_resource = resources_head

    # Add a new record for the module
    record_module(module, subscription_plan_id)

if __name__ == '__main__':
    upload()
