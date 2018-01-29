from contextlib import contextmanager
from functools import partial, reduce
import json
import logging
import itertools
import operator
import copy

from mock import mock
from six import add_metaclass

from ..tools import ValidationError, cached_property


logger = logging.getLogger(__name__)


# pylint: disable=W0212, W0613


class Q(object):
    AND = 'AND'
    OR = 'OR'

    def __init__(self, *args, **kwargs):
        self.connector = Q.AND
        self.negated = False
        self.children = list(args)
        self.children += list(kwargs.items())

    def merge(self, connector, other):
        assert isinstance(other, Q)
        if not self.negated and not other.negated:
            if self.connector == connector and other.connector == connector:
                clone = self.clone()
                clone.children += other.clone().children
                return clone
            elif self.connector == connector and other.connector != connector:
                clone = self.clone()
                clone.children.append(other.clone())
                return clone
            elif self.connector != connector and other.connector == connector:
                clone = other.clone()
                clone.children.append(self.clone())
                return clone
        return Q.with_connector(connector, False, self, other)

    def __and__(self, other):
        return self.merge(Q.AND, other)

    def __or__(self, other):
        return self.merge(Q.OR, other)

    def __invert__(self):
        clone = self.clone()
        clone.negated = not clone.negated
        return clone

    @classmethod
    def with_connector(cls, connector, negated, *args, **kwargs):
        q = cls(*args, **kwargs)
        q.connector = connector
        q.negated = negated
        return q

    def clone(self):
        return Q.with_connector(self.connector, self.negated, *copy.deepcopy(self.children))


NOT_PROVIDED = object()


class Field(object):
    # pylint: disable=R0902, R0913
    def __init__(self, primary_key=False, editable=True, null=False, blank=False,
                 default=NOT_PROVIDED, help_text='', validators=None, verbose_name=None,
                 choices=None, name=None):
        self.primary_key = primary_key
        self.editable = editable
        self.null = null
        self.blank = blank
        self.default = default
        self.help_text = help_text
        self.validators = validators
        self.verbose_name = verbose_name
        self.choices = choices
        self.model = None
        self.name = name
        self.attname = None

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name
        self.attname = name
        if self.verbose_name is None and self.name:
            self.verbose_name = self.name.replace('_', ' ')

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)
        self.model = cls
        cls._meta.add_field(self)
        if self.choices:
            setattr(cls, 'get_%s_display' % self.name,
                    partial(cls._get_FIELD_display, field=self))

    def _get_FIELD_display(self, field):
        value = getattr(self, field.attname)
        return str(dict(field.flatchoices).get(value, value))

    def get_default(self):
        return self.default if self.has_default() else None

    def has_default(self):
        return self.default is not NOT_PROVIDED


class JsonField(Field):
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        """
        :param base_type: list | dict
        :type base_type: type
        :rtype: JsonField[T]
        """
        self.base_type = kwargs['base_type']
        del kwargs['base_type']
        super(JsonField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """:rtype: T"""
        def check_base_type(val):
            if not isinstance(val, self.base_type):
                raise ValidationError(
                    "Invalid JSON type. Got {}, expected {}".format(type(parsed), self.base_type))
            return val

        if value is None:
            return None
        if isinstance(value, self.base_type):
            return value
        if not value and self.null:
            return None
        try:
            parsed = json.loads(value)
            return check_base_type(parsed)
        except (ValueError, TypeError) as _:
            raise ValidationError("Invalid JSON")

    @property
    def empty_values(self):
        return ['', [], {}]


class IntegerField(JsonField):
    def __init__(self, **kwargs):
        super(IntegerField, self).__init__(base_type=int, **kwargs)


class CharField(JsonField):
    def __init__(self, choices=None, **kwargs):
        super(CharField, self).__init__(base_type=str, **kwargs)


class BooleanField(JsonField):
    def __init__(self, **kwargs):
        super(BooleanField, self).__init__(base_type=bool, **kwargs)


class FloatField(JsonField):
    def __init__(self, **kwargs):
        super(FloatField, self).__init__(base_type=float, **kwargs)


class NoDbQuery(object):
    def __init__(self, q=None, ordering=None):
        self._q = q
        self._ordering = [] if ordering is None else ordering

    def can_filter(self):
        return True

    def add_q(self, q):
        self._q = q if self._q is None else self._q & q

    def clone(self):
        tmp = NoDbQuery()
        tmp._q = self._q.clone() if self._q is not None else None
        tmp._ordering = self._ordering[:]
        return tmp

    def clear_ordering(self, force_empty=None):
        self._ordering = []

    def add_ordering(self, *keys):
        self._ordering += keys

    @property
    def ordering(self):
        return self._ordering

    @property
    def q(self):
        """:rtype: Q"""
        return self._q

    def set_empty(self):
        self.clear_ordering()
        self._q = None

    def __str__(self):
        return "<NoDbQuery q={}, ordering={}>".format(self._q, self._ordering)


class NodbQuerySet(object):

    def __init__(self, model=None, hints=None, request=None, context=None):
        """
        model parameter needs to be optional, as QuerySet.__deepcopy__() sets self.model afterwards.
        """
        self.model = model
        self._context = context
        self._current = 0
        self._query = NoDbQuery()

    @cached_property
    def _max(self):
        return len(self._filtered_data) - 1

    def _data(self):
        context = self._context if self._context else NodbManager.nodb_context
        objects = self.model.get_all_objects(context, query=self._query)
        self_pointer = LazyProperty.QuerySetPointer(objects)
        for obj in objects:
            #  Because we're calling the model constructors ourselves, django thinks that
            #  the objects are not in the database. We need to "hack" this.
            obj._state.adding = False
            obj._query_set_pointer = self_pointer

        return objects

    @cached_property
    def _filtered_data(self):
        """
        Each Q child consists of either another Q, `attr__iexact` or `model__attr__iexact` or `attr`
        """
        def _filter_by_modifier(keys, attr, value):
            modifier = keys[1] if len(keys) > 1 else "exact"
            if modifier == "exact":
                return attr == attr.__class__(value)
            elif modifier == "istartswith":
                return attr.startswith(value)
            elif modifier == "icontains":
                return value in attr
            elif modifier == "in":
                return attr in value
            else:
                raise ValueError('Unsupported Modifier {}.'.format(modifier))

        def filter_impl(keys, value, obj):
            # pylint: disable=R1701
            assert keys

            if isinstance(obj, dict):
                if keys[0] not in obj:
                    raise AttributeError(
                        'Attribute {} does not exist in dict'.format(keys[0]))
            elif not hasattr(obj, keys[0]):
                raise AttributeError(
                    'Attribute {} does not exist for {}'.format(keys[0], obj.__class__))

            attr = obj[keys[0]] if isinstance(obj, dict) else getattr(obj, keys[0], None)

            if attr is None:
                return value is None
            elif isinstance(attr, list):
                if isinstance(attr[0], str):
                    return _filter_by_modifier(keys, attr, value)
                return reduce(operator.or_, [filter_impl(keys[1:], value, e) for e in attr], False)
            elif isinstance(attr, NodbModel) or isinstance(attr, dict):
                return filter_impl(keys[1:], value, attr)
            else:
                return _filter_by_modifier(keys, attr, value)

        def filter_one_q(q, obj):
            """
            :type q: Q
            :type obj: NodbModel
            :rtype: bool
            """
            def negate(res):
                # pylint: disable=R1705
                return not res if q.negated else res

            # pylint: disable=R1705

            if q is None:
                return True
            elif isinstance(q, tuple):
                return filter_impl(q[0].split('__'), q[1], obj)
            elif q.connector == "AND":
                return negate(reduce(lambda l, r: l and filter_one_q(r, obj), q.children, True))
            else:
                children = {c for c in q.children if not isinstance(c, Q) or c.children}
                return negate(reduce(lambda l, r: l or filter_one_q(r, obj), children, False))

        filtered = [obj for obj in self._data()
                    if filter_one_q(self._query.q, obj)]

        # pylint: disable=W0640
        for order_key in self.query.ordering[::-1]:
            if order_key.startswith("-"):
                order_key = order_key[1:]
                filtered.sort(key=lambda obj: getattr(obj, order_key), reverse=True)
            else:
                filtered.sort(key=lambda obj: getattr(obj, order_key))

        return filtered

    def __iter__(self):
        self._current = 0
        return self

    def __len__(self):
        return len(self._filtered_data)

    def next(self):
        if self._current > self._max:
            raise StopIteration
        else:
            self._current += 1
            return self._filtered_data[self._current - 1]

    def __next__(self):
        return self.next()

    def __getitem__(self, index):
        return self._filtered_data[index]

    def _clone(self, klass=None, setup=False, **kwargs):
        my_clone = NodbQuerySet(self.model, context=self._context)
        my_clone._query = self._query.clone()
        return my_clone

    def __deepcopy__(self, memo):
        obj = self.__class__()
        for k, v in self.__dict__.items():
            obj.__dict__[k] = copy.deepcopy(v, memo)
        return obj

    def count(self):
        return len(self._filtered_data)

    # pylint: disable=R1710
    def get(self, **kwargs):
        """Return a single object filtered by kwargs."""
        filtered_data = self.filter(**kwargs)

        # Thankfully copied from
        # https://github.com/django/django/blob/1.7/django/db/models/query.py#L351
        num = len(filtered_data)
        if num == 1:
            return filtered_data[0]
        if not num:
            raise self.model.DoesNotExist(
                '{} matching query "{}" does not exist.'.format(self.model._meta.object_name,
                                                                filtered_data.query))
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s!" % (
                self.model._meta.object_name,
                num
            )
        )

    def exists(self):
        return bool(self._filtered_data)

    @property
    def query(self):
        return self._query

    def filter(self, *args, **kwargs):
        clone = self._clone()
        clone.query.add_q(Q(*args, **kwargs))
        return clone

    def exclude(self, *args, **kwargs):
        clone = self._clone()
        clone.query.add_q(~Q(*args, **kwargs))
        return clone

    def all(self):
        return self._clone()

    def order_by(self, *keys):
        clone = self._clone()
        for k in keys:
            clone.query.add_ordering(k)
        return clone

    def __repr__(self):
        data = list(self[:20])
        if len(data) > 19:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def __nonzero__(self):
        return bool(len(self))

    def __bool__(self):
        return bool(len(self))


class NodbManager(object):

    nodb_context = None

    def __init__(self):
        self.model = None
        self._hints = None

    @classmethod
    def set_nodb_context(cls, context):
        cls.nodb_context = context

    def contribute_to_class(self, cls, name):
        clone = copy.deepcopy(self)
        clone.model = cls
        setattr(cls, name, clone)

    def copy_manager_to(self, new_class):
        new_class.add_to_class('objects', self)

    def get_queryset(self):
        return NodbQuerySet(self.model, context=NodbManager.nodb_context)

    def all(self):
        return self.get_queryset().all()

    def get(self, **kwargs):
        return self.get_queryset().get(**kwargs)

    def filter(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs)


class LazyProperty(object):
    """
    See also: django.db.models.query_utils.DeferredAttribute

    Internally used by @bulk_attribute_setter().
    """
    class QuerySetPointer(object):
        def __init__(self, target):
            self.target = target

    def __init__(self, field_name, eval_func, catch_exceptions, field_names):
        self.field_name = field_name
        self.eval_func = eval_func
        self.catch_exceptions = catch_exceptions
        self.field_names = field_names

    def __get__(self, instance, owner=None):
        """
        runs eval_func which fills some lazy properties.
        """
        if hasattr(instance, '_query_set_pointer'):
            query_set = instance._query_set_pointer.target
        else:
            # Fallback. Needed for objects without a queryset.
            query_set = [instance]
        if self.field_name in instance.__dict__:
            return instance.__dict__[self.field_name]

        if self.catch_exceptions is None:
            self.eval_func(instance, query_set, self.field_names)
        else:
            try:
                self.eval_func(instance, query_set, self.field_names)
            except self.catch_exceptions as _:
                # logger.exception('failed to populate Field "{}" of {} ({})'
                #                  .format(self.field_name, str(instance), instance.__class__))
                fields = instance.__class__.make_model_args({}, fields_force_none=self.field_names)
                for field_name, value in list(fields.items()):
                    setattr(instance, field_name, value)

        if self.field_name not in instance.__dict__:
            raise KeyError(
                'LazyProperty: {} did not set {} of {}'.format(self.eval_func, self.field_name,
                                                               instance))
        return instance.__dict__[self.field_name]

    def __set__(self, instance, value):
        """
        Deferred loading attributes can be set normally (which means there will
        never be a database lookup involved.
        """
        instance.__dict__[self.field_name] = value


def bulk_attribute_setter(field_names, catch_exceptions=None):
    """
    The idea behind @bulk_attribute_setter is to delay expensive calls to librados, until someone
    really needs the information gathered in this call. If the attribute is never used, the call
    will never be executed. In general, this is called lazy execution.

    Before, NodbQuerySet called self.model.get_all_objects to generate a list of objects. The
    implementations of get_all_objects were calling the librados commands to fill all attributes,
    even if they were never accessed.

    Because a field may never be accessed, this can generate better performance than caching,
    especially if the cache is cold.

    The bulk_attribute_setter decorator can be used like so:
    >>> class MyModel(NodbModel):
    >>>     my_field = models.IntegerField()
    >>>
    >>>     @bulk_attribute_setter(['my_field'])
    >>>     def set_my_field(self, objs, field_names):
    >>>         self.my_field = 42

    Keep in mind, that you can set the my_field attribute on all objects, not just self.

    The decorator modifies the model to look like this:
    >>> def set_my_field(self, objs):
    >>>     self.my_field = 42
    >>>
    >>> class MyModel(NodbModel):
    >>>     my_field = models.IntegerField()
    >>>     set_my_field = LazyPropertyContributor(['my_field'], set_my_field)

    A LazyPropertyContributor property implements the contribute_to_class method, which modifies
    the model itself to look like so:
    >>> class MyModel(NodbModel):
    >>>     my_field = LazyProperty('my_field', set_my_field)

    The my_field field is not overwritten, because the fields are already moved into the _meta class
    at this point. If someone then accesses the my_field attribute, LazyProperty.__get__ is called,
    which then calls set_my_field to set the field, as if one had written:
    >>> instances = MyModel.objects.all()
    >>> set_my_field(instances[0], instances)
    >>> assert instances[0].my_field == 42

    For example, get_all_objects generates a QuerySet like this:

    id	name	  disk_usage
    0	'foo'     LazyProperty('disk_usage')
    1	'bar'	  LazyProperty('disk_usage')

    When accessing bar.disk_usage, LazyProperty calls `ceph df` and fills the queryset like so:

    id	name	disk_usage
    0	'foo'   1MB
    1	'bar'  	2MB

    :type field_names: list[str]
    :param catch_exceptions: Exceptions that will be caught. In case of an exception, all
        `field_names` will be set to None.
    :type catch_exceptions: exceptions.Exception | tuple[exceptions.Exception]
    """

    if not field_names:
        raise ValueError('`field_names` must not be empty.')

    class LazyPropertyContributor(object):
        def __init__(self, field_names, func):
            self.field_names = field_names
            self.func = func

        def contribute_to_class(self, cls, name, virtual_only=False):
            for name2 in self.field_names:
                setattr(cls, name2, LazyProperty(name2, self.func, catch_exceptions,
                                                 self.field_names))

    def decorator(func):
        return LazyPropertyContributor(field_names, func)

    return decorator


class NodbDoesNotExist(Exception):
    pass


class NodbMultipleObjectsReturned(Exception):
    pass


def subclass(name, parents, class_dict=None):
    if class_dict is None:
        class_dict = {}
    return type(name, tuple(parents), class_dict)


class NodbOptions(object):
    def __init__(self, meta):
        self.meta = meta
        self.pk = None
        self.fields = []
        self.unique_together = None
        self.object_name = None
        self.model = None
        self.model_name = None

    def _prepare(self, model):
        if self.pk is None:
            auto = IntegerField(verbose_name='ID', primary_key=True)
            model.add_to_class('id', auto)

    def contribute_to_class(self, cls, name):

        cls._meta = self
        self.model = cls
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.model_name = self.object_name.lower()

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name2 in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name2.startswith('_'):
                    del meta_attrs[name2]
            # from django.db.models.options import DEFAULT_NAMES
            # for attr_name in DEFAULT_NAMES:
            #    if attr_name in meta_attrs:
            #        setattr(self, attr_name, meta_attrs.pop(attr_name))
            #    elif hasattr(self.meta, attr_name):
            #        setattr(self, attr_name, getattr(self.meta, attr_name))

            # unique_together can be either a tuple of tuples, or a single
            # tuple of two strings. Normalize it to a tuple of tuples, so that
            # calling code can uniformly expect that.
            ut = meta_attrs.pop('unique_together', self.unique_together)
            if ut and not isinstance(ut[0], (tuple, list)):
                ut = (ut,)
            self.unique_together = ut

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError(
                    "'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        del self.meta

    @property
    def concrete_fields(self):
        return self.fields

    @property
    def concrete_model(self):
        return self.model

    def get_field_by_name(self, name):
        for field in self.fields:
            if field.attname == name:
                return field
        raise KeyError('No field named "{}" in model "{}".'.format(name, str(self.model)))

    def setup_pk(self, field):
        if not self.pk and field.primary_key:
            self.pk = field

    def add_field(self, field):
        self.fields.append(field)
        self.setup_pk(field)


class NodbModelMeta(type):
    # Copy from django.db.models.base.ModelBase#__new__
    def __new__(mcs, name, bases, attrs):
        # Create the class.
        dunders = {k: v for k, v in attrs.items() if k in ['__module__', '__doc__', '__init__']}
        for k in dunders:
            del attrs[k]
        new_class = super(NodbModelMeta, mcs).__new__(mcs, name, bases, dunders)
        attr_meta = attrs.pop('Meta', None)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta

        # Figure out the app_label by looking one level up.
        # For 'django.contrib.sites.models', this would be 'sites'.
        new_class.add_to_class('_meta', NodbOptions(meta))
        new_class.add_to_class('DoesNotExist', subclass('DoesNotExist', [NodbDoesNotExist]))
        new_class.add_to_class('MultipleObjectsReturned',
                               subclass('MultipleObjectsReturned', [NodbMultipleObjectsReturned]))

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        new_class._meta._prepare(new_class)

        if 'objects' not in attrs:
            bases[0].objects.copy_manager_to(new_class)

        return new_class

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


@add_metaclass(NodbModelMeta)
class NodbModel(object):

    objects = NodbManager()

    @staticmethod
    def get_all_objects(api_controller, query):
        msg = 'Every NodbModel must implement its own get_all_objects() method.'
        raise NotImplementedError(msg)

    def get_modified_fields(self, update_fields=None, **kwargs):
        """
        Returns a dict of fields, which have changed. There are two known problems:

        1. There is a race between get_modified_fields and the call to this.save()
        2. A type change, e.g. str and unicode is not handled.

        :param update_fields: restrict the search for updated fields to update_fields.
        :param kwargs: used to retrieve the original. default: `pk`
        :rtype: tuple[dict[str, Any], T <= NodbModel]
        :return: A tuple consisting of the diff and the original model instance
        """
        if not kwargs:
            kwargs['pk'] = self.pk

        field_names = [f.attname for f in self.__class__._meta.fields]
        if update_fields is None:
            update_fields = field_names
        else:
            assert not set(update_fields) - set(field_names)

        fields = [f for f in self.__class__._meta.fields if f.attname in update_fields]
        original = self.__class__.objects.get(**kwargs)
        return {
            field.attname: getattr(self, field.attname, None)
            for field
            in fields
            if field.editable and getattr(self, field.attname, None) != getattr(original,
                                                                                field.attname, None)
        }, original

    def attribute_is_unevaluated_lazy_property(self, attr):
        """
        :rtype: bool
        """
        if attr not in self.__class__.__dict__:
            return False
        prop = self.__class__.__dict__[attr]
        if not isinstance(prop, LazyProperty):
            return False
        return attr not in self.__dict__

    def set_read_only_fields(self, obj, include_pk=True):
        """
        .. example::
            >>> insert = self.id is None
            >>> diff, original = self.get_modified_fields(name=self.name) if insert
            >>>     else self.get_modified_fields()
            >>> if not insert:
            >>>     self.set_read_only_fields()
        """
        if include_pk:
            self.pk = obj.pk

        for field in self.__class__._meta.fields:
            if (not field.editable
               and not self.attribute_is_unevaluated_lazy_property(field.attname)
               and hasattr(obj, field.attname)
               and getattr(self, field.attname, None) != getattr(obj, field.attname)):
                setattr(self, field.attname, getattr(obj, field.attname))

    @classmethod
    def make_model_args(cls, json_result, fields_force_none=None):
        """
        TODO: fields_force_none could be auto generated by the field names.

        :type json_result: dict[str, Any]
        :type fields_force_none: list[str]
        :rtype: dict[str, Any]
        """
        def get_val_from_json(key):
            if key in json_result:
                return json_result[key]
            elif key.replace('_', '-') in json_result:
                # '-' is not supported for field names, but used by ceph.
                return json_result[key.replace('_', '-')]
            raise AttributeError

        def handle_field(field):
            """:rtype: list[tuple[str, Any]]"""
            try:
                val = get_val_from_json(field.attname)
            except AttributeError:
                return []

            if val is None and not field.null:
                return []

            try:
                python_val = field.to_python(val)
            except ValidationError as _:
                return []

            return [(field.attname, python_val)]

        model_args = dict(
            itertools.chain.from_iterable([handle_field(field) for field in cls._meta.fields])
        )
        for name in fields_force_none or []:
            if name not in model_args:
                model_args[name] = None
        return model_args

    def __init__(self, *args, **kwargs):
        self._state = mock.Mock()

        for k, w in kwargs.items():
            self.__dict__[k] = w  # __dict__ is a dictproxy

        for field in self._meta.concrete_fields:
            # set defaults:
            if not self.attribute_is_unevaluated_lazy_property(field.name) \
               and not hasattr(self, field.name):
                setattr(self, field.name, field.get_default())

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """
        This base implementation does nothing, except telling django that self is now successfully
        inserted.
        """
        self._state.adding = False

    def full_clean(self, exclude=None, validate_unique=True):
        """
        copy from django.db.models.base.Model#full_clean
        """
        errors = {}
        if exclude is None:
            exclude = []

        try:
            self.clean_fields(exclude=exclude)
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Form.clean() is run even if other validation fails, so do the
        # same with Model.clean() for consistency.
        try:
            self.clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # Run unique checks, but only for fields that passed validation.
        if validate_unique:
            for name in errors.keys():
                if name not in exclude:
                    exclude.append(name)
            try:
                self.validate_unique(exclude=exclude)
            except ValidationError as e:
                errors = e.update_error_dict(errors)

        if errors:
            raise ValidationError(errors)

    def clean(self, exclude=None, validate_unique=True):
        return self.full_clean(exclude, validate_unique)

    @property
    def pk(self):
        return getattr(self, self._meta.pk.attname)

    @pk.setter
    def pk(self, value):
        setattr(self, self._meta.pk.attname, value)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.pk == other.pk


@contextmanager
def nodb_context(ctx):
    old_ctx = NodbManager.nodb_context
    try:
        NodbManager.set_nodb_context(ctx)
        yield
    finally:
        NodbManager.set_nodb_context(old_ctx)
