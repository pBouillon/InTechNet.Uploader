from dataclasses import dataclass


@dataclass(init=True)
class Resource:
    '''Represent a resource of a module'''
    content: str
    name: str
    next_resource: 'Resource' = None


@dataclass(init=True)
class Module:
    '''Represent a module'''
    description: str
    name: str
    first_resource: Resource = None
