from django.db import models

from .manager import SharedMemoryManager

from . import tls  # thread local storage


class SharedMemoryModel(models.Model):
    """
    Abstract class to derive any shared memory model from

    :ivar use_strong_refs: should one use strong refs or not for instances.
        False by default. If True, instances will be kept in the cache until
        explicitly flushed
    """

    objects = SharedMemoryManager()

    use_strong_refs = False
    multi_db = False

    class Meta:
        # does not inherit from base_class.Meta but that's not an issue
        abstract = True

    # OVERRIDES

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        This method will either create an instance (by calling the default
        implementation) or try to retrieve one from the class-wide cache by
        infering the pk value from args and kwargs. The cache is then populated
        whenever possible (ie when it is possible to infer the pk value).
        """
        if cls._deferred:
            args = ()
            kwargs = dict(zip(field_names, values))
        else:
            args = values
            kwargs = {}
        instance_key = cls._get_cache_key(args, kwargs)

        def create_instance():
            inst = cls(*args, **kwargs)
            inst._state.adding = False
            inst._state.db = db
            cls.cache_instance(inst)
            return inst

        # depending on the arguments, we might not be able to infer the PK
        # in that case, we create a new instance
        if instance_key is None:
            return create_instance()
        else:
            instance = cls.get_cached_instance(instance_key, db)
            if instance is None:
                return create_instance()
            else:
                return instance


    # DJANGO-IDMAP METHODS

    @classmethod
    def _get_cache_key(cls, args, kwargs):
        """
        This method is used by the caching subsystem to infer the PK value
        from the constructor arguments. It is used to decide if an instance
        has to be built or is already in the cache.
        """

        result = None
        # Quick hack for my composites work for now.
        if hasattr(cls._meta, 'pks'):
            pk = cls._meta.pks[0]
        else:
            pk = cls._meta.pk

        pk_position = getattr(cls._meta, 'pk_pos', None)
        if pk_position is None:
            # the pk position could not be extracted from _meta
            # calculate it ...
            pk_position = cls._meta.fields.index(pk)
            # ... and store it
            setattr(cls._meta, 'pk_pos', pk_position)

        if len(args) > pk_position:
            # if it's in the args, we can get it easily by index
            result = args[pk_position]
        elif pk.attname in kwargs:
            # retrieve the pk value. Note that we use attname instead of name,
            # to handle the case where the pk is a ForeignKey.
            result = kwargs[pk.attname]
        elif pk.name != pk.attname and pk.name in kwargs:
            # ok we couldn't find the value, but maybe it's a FK and we can
            # find the corresponding object instead
            result = kwargs[pk.name]

        if result is not None and isinstance(result, models.Model):
            # if the pk value happens to be a model instance (which can
            # happen with a FK), we'd rather use its own pk as the key
            result = result._get_pk_val()
        return result

    @classmethod
    def get_cached_instance(cls, pk, db=None):
        """
        Method to retrieve a cached instance by pk value and db. Returns None
        when not found (which will always be the case when caching is disabled
        for this class). Please note that the lookup will be done even when
        instance caching is disabled.
        """
        return tls.get_cached_instance(cls, pk, db)

    @classmethod
    def cache_instance(cls, instance):
        """
        Method to store an instance in the cache.
        """
        pk = instance._get_pk_val()
        if pk is not None:
            tls.cache_instance(cls, instance)

    @classmethod
    def flush_cached_instance(cls, instance):
        """
        Method to flush an instance from the cache. The instance will always
        be flushed from the cache, since this is most likely called from
        delete(), and we want to make sure we don't cache dead objects.
        """
        tls.flush_cached_instance(cls, instance)

    @classmethod
    def flush_instance_cache(cls, db=None, flush_sub=False):
        tls.get_cache(cls, flush=db)
        if flush_sub:
            for s in cls.__subclasses__():
                s.flush_instance_cache(db, flush_sub)

    def save(self, *args, **kwargs):
        """
        Caches the instance on save
        """
        super(SharedMemoryModel, self).save(*args, **kwargs)
        self.__class__.cache_instance(self)
