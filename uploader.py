import click
from pathlib import Path
from typing import List
import yaml

from utils.dataclasses import Module, Resource


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


@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option(
    '--module',
    '-m',
    'module',
    help='Path to the module description file',
    type=click.Path(exists=True))
def upload(path, module):
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


if __name__ == '__main__':
    upload()
