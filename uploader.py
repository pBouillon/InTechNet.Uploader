from configparser import ConfigParser
import click
from pathlib import Path
import psycopg2
from typing import List
import yaml

from utils.dataclasses import Module, Resource


def extract_config(filename='database.ini', section='postgresql') -> dict:
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


def get_sorted_resources(resources: List[Resource]) -> List[Resource]:
    '''Link all provided resource by alphabetical order'''
    # Make a copy of all resource
    sorted_resources = resources[:]
    
    # Sort the copy and return it
    sorted_resources.sort(key=lambda resource: resource.name)
    return sorted_resources


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


def record_module(
    module: Module, subscription_plan_id: int,
    config: dict = extract_config()) -> int:
    '''Record the provided module in database'''
    
    sql = '''
       INSERT INTO "module" ("ModuleDescription", "SubscriptionPlanId", "ModuleName")
       VALUES(%s, %s, %s) RETURNING "Id";
    '''
    
    conn = None
    module_id = 0
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**config)
        # Create a new cursor
        cur = conn.cursor()
        # Execute the INSERT statement
        cur.execute(sql, (module.description, subscription_plan_id, module.name))
        # get the generated id back
        module_id = int(cur.fetchone()[0])
        # Commit the changes to the database
        conn.commit()
        # Close communication with the database
        cur.close()
    finally:
        if conn is not None:
            conn.close()
    
    return module_id


def record_resource(
    resource: Resource, module_id: int, next_resource_id: int,
    config: dict = extract_config()) -> int:
    '''Record the provided resource in database'''
    
    sql = '''
       INSERT INTO "resource" ("ModuleId", "Content", "NextResourceId")
       VALUES(%s, %s, %s) RETURNING "Id";
    '''
    conn = None
    resource_id = 0
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**config)
        # Create a new cursor
        cur = conn.cursor()
        # Execute the INSERT statement
        cur.execute(sql, (module_id, resource.content, next_resource_id))
        # get the generated id back
        resource_id = int(cur.fetchone()[0])
        # Commit the changes to the database
        conn.commit()
        # Close communication with the database
        cur.close()
    finally:
        if conn is not None:
            conn.close()

    return resource_id


def record_resources(
        resources: List[Resource], module_id: int,
        config: dict = extract_config()) -> int:
    '''Record the provided resources in database'''
    # Since all resources are linked to each other, we need the index of the
    # second resource to track the first
    # To achieve that, we need to invert the order and start tracking the last
    # which is not linked to any other resource
    resources = resources[::-1]
    
    next_resource_id = None
    for resource in resources:
        next_resource_id = record_resource(resource, module_id, next_resource_id, config)


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
    resources = get_sorted_resources(resources)

    # Retrieve module meta data
    module_path = Path(module if module else path)
    module = get_module(module_path)
    
    # Add a new record for the module
    module_id = record_module(module, subscription_plan_id)
    
    # Add a new track for all its associated resources
    record_resources(resources, module_id)

if __name__ == '__main__':
    upload()
