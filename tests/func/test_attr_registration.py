"""Tests for attribute registration on an arbitrary pydantic.BaseModel using pydantic-modelable.Modelable."""
import pytest
from pydantic import BaseModel
from pydantic_core import ValidationError

from pydantic_modelable import Modelable


@pytest.mark.parametrize(
    'optional,with_factory,with_args,factory_none',
    (
        (True, True, False, False),
        (True, True, False, True),
        (True, True, True, False),
        (True, True, True, True),
        (True, False, False, False),
        (False, True, False, None),
        (False, True, True, None),
        (False, False, False, None),
    ),
    ids=[
        'defaulted',
        'defaulted-none',
        'implicit',
        'implicit-none',
        'opt-unspecified',
        'notdefaulted-noargs',
        'notdefaulted-args',
        'explicit',
    ],
)
def test_register_attribute(optional: bool, with_factory: bool, with_args: bool, factory_none: bool | None) -> None:
    """Test that the attribute is properly registered, and can be used as one would expect."""
    expected_subname: str|None = None

    class Registrar(Modelable):
        ...

    if with_args:
        if with_factory:
            def default_factory_1() -> 'Registered | None':
                nonlocal expected_subname
                expected_subname = 'specified'
                return Registered(subname='specified') if not factory_none else None

        @Registrar.as_attribute('attr', optional=optional, default_factory=default_factory_1 if with_factory else None)
        class Registered(BaseModel):
            subname: str

    else:
        if with_factory:
            def default_factory_2() -> 'DefaultedRegistered | None':
                return DefaultedRegistered(**{}) if not factory_none else None

        expected_subname = 'defaulted'
        @Registrar.as_attribute('attr', optional=optional, default_factory=default_factory_2 if with_factory else None)
        class DefaultedRegistered(BaseModel):
            subname: str = 'defaulted'

    Registrar.model_rebuild(force=True)

    #
    # Check that we can use it as expected:
    #
    # Check 1: Unable to instanciate container model without specifying args
    if not with_factory and (optional or with_args):
        with pytest.raises(ValidationError):
            r1 = Registrar()

    # Check 2: Args must be specified, no default value provided
    if all([not with_factory, with_args, not factory_none]):
        if optional:
            r1 = Registrar(**{'attr': None})
            assert getattr(r1, 'attr') is None
        else:
            expected_subname = 'test'
            r1 = Registrar(**{'attr': {'subname': 'test'}})
            assert getattr(getattr(r1, 'attr'), 'subname') == expected_subname

    # Check 3: Ensure default_factory is applied properly
    if with_factory:
        r1 = Registrar()
        if factory_none:
            assert getattr(r1, 'attr') is None
        else:
            assert getattr(getattr(r1, 'attr'), 'subname') == expected_subname

    # Check 4: Check embedded default values
    if not with_args:
        r1 = Registrar(**{'attr': {}})
        assert getattr(getattr(r1, 'attr'), 'subname') == expected_subname

    # Check 5: Check value with specified
    r1 = Registrar(**{'attr': {'subname': 'mytest'}})
    assert getattr(getattr(r1, 'attr'), 'subname') == 'mytest'
