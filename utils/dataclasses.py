from dataclasses import dataclass


@dataclass(init=True)
class Resource:
    '''Represent a resource of a module'''
    content: str
    name: str


@dataclass(init=True)
class Module:
    '''Represent a module'''
    description: str
    name: str
