django-idmap
============

|copyright| 2014-2017 Thomas Khyn
|copyright| 2009 David Cramer

An identity mapper for the Django ORM. This is a fork of django-idmapper_,
which is no longer maintained.

``django-idmap`` has been tested against django 1.8, 1.11 and 2.0 and the
latest minor versions of Python 2 and 3 (Django 2.0 only supports Python 3).

If you like django-gm2m and are looking for a way to thank me and/or encourage
future development, here is my BTC or BCH donation address:
``1EwENyR8RV6tMc1hsLTkPURtn5wJgaBfG9``.


What is it?
-----------

``django-idmap`` is a Django application which:

- loads only once the instances in memory the first time they are needed
- shares them throughout your interpreter until the request is finished

Indeed, the default Django behavior is to expose different instances for the
same database entry between the start and the end of the request. It has one
main consequence: the temporary attributes you may set are lost if you want
to access the same database object in another place in your code.

.. warning::

   Deserialization (such as from the cache) will *not* use the identity mapper.

Tested with django 1.8+ and latest minor versions of python 2 and 3.

Installation
------------

As straightforward as it can be, using pip::

   pip install django-idmap

You also need to add ``'idmap'`` to the ``INSTALLED_APPS`` setting.


Quick start
-----------

To enable the identity mapper for a model, you simply need to make it inherit
from ``idmap.models.IdMapModel`` instead of ``django.db.models.Model``.

.. tip::

   You can import ``idmap.models`` as you would import ``django.db.models``.
   ``idmap.models`` exposes all that is exposed by ``django.db.models`` plus
   the ``IdMapModel`` model class.

You may of course mix and match ``IdMapModel`` and ``Model``::

    from idmap import models

    class MyModel(models.IdMapModel):
        name = models.CharField(...)
        fkey = models.ForeignKey('Other', on_delete=models.CASCADE)

    class Other(models.Model):
        name = models.CharField(...)

2 caching modes are available:

- Weak references mode: the instance will be removed from the cache once there
  are no more references to it. This is the default behavior
- Strong references mode: the instance will be loaded only once from the
  database and will be removed from the cache when it is flushed

If you want to use strong references for a particular model, simply set
``use_strong_refs`` to ``True`` in the derived model class' ``Meta``::

   from idmap import models

   class MyModel(models.IdMapModel):
      class Meta:
         use_strong_refs = True
      [...]


Manual operations
-----------------

In most cases, that's all there is to do with ``django-idmap``. Sometimes, you
may need to flush the cache manually before the request is finished.

You can use:

- ``idmap.flush()`` to erase the whole cache
- ``IdMapModel.flush_instance_cache()`` to erase the cache for one model
- ``IdMapModel.flush_cached_instance(instance)`` to erase one instance
  from the cache

Signals
-------

``idmap.signals.pre_flush`` and ``idmap.signals.post_flush`` are sent before -
respectively after - the cache is flushed. Connect handlers to these if you
need to run code at these moments.

.. warning:

   ``pre_flush`` and ``post_flush`` are only sent when the ``flush`` function
   is used or when the cache is automatically flushed (when the request ends).


``django-idmap`` flushes the cache when the ``request_finished`` or
``post_migrate`` signal are sent. This default behavior may be modified (at
your own risk!) by disconnecting the ``idmap.signals.flush_idmap`` handler
from these signals.


Multiple database support
-------------------------

In some cases, you may need to store instances of the same model in several
databases. It is possible to tell ``django-idmap`` to also take the database
into account when creating or getting instances::

   class MyModel(models.IdMapModel):
      class Meta:
         multi_db = True
      [...]

This way, ``instance1_1`` with primary key ``1`` in database ``db1`` will be
different from ``instance2_1`` with primary key ``1`` in database ``db2``::

   >>> MyModel.objects.using('db1').create(pk=1)
   >>> MyModel.objects.using('db2').create(pk=1)
   >>> idmap.flush()
   >>> instance1_1 = MyModel.objects.using('db1').get(pk=1)
   >>> instance2_1 = MyModel.objects.using('db2').get(pk=1)
   >>> assert instance1_1 is instance 2_1
   AssertionError

When using multiple databases, you may also flush only one database by
providing its name to ``idmap.flush()``::

   >>> idmap.flush('db1')

will only flush instances that were retrieved using the database ``db1``.
``IdMapModel.flush_instance_cache`` can also take a ``db`` argument.

Similarly, a keyword-argument ``db`` is provided when the ``pre_flush`` and
``post_flush`` signals are sent. ``db`` is ``None`` if all databases are
flushed (i.e. if no database alias was provided).


Proxy models
------------

All instances of models and proxy models using the same base concrete class
(let's call this a proxy family) are stored in the same cache, and are
accessible through all the members of the proxy family::

   >>> class MyProxyModel(MyModel):
   >>>     class Meta:
   >>>         proxy = True
   >>> original = MyModel.objects.create(pk=1)
   >>> proxy = MyProxyModel.objects.create(pk=2)
   >>> assert original is MyProxyModel.get(pk=1)


Inheritance catch-ups
---------------------

In case you need to use a custom manager or custom metaclass on a model based
on ``IdMapModel``, you need to derive them from ``idmap``'s own manager and
metaclass::

   >>> class MyModelBase(models.IdMapModelBase):
   >>>     [...]
   >>> class MyManager(models.IdMapManager):
   >>>     [...]
   >>> class MyModel(models.IdMapModel,
                     metaclass=MyModelBase): # on python 3
   >>>     __metaclass__ = MyModelBase  # on python 2
   >>>     objects = MyManager()


References
----------

David Cramer's django-idmapper_

Original code and concept: http://code.djangoproject.com/ticket/17

.. |copyright| unicode:: 0xA9
.. _django-idmapper: https://github.com/dcramer/django-idmapper
