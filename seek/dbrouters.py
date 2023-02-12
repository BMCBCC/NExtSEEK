class CustomRouter(object):

    def db_for_read(self, model, **hints):
        return getattr(model, "_DATABASE", "default")

    def db_for_write(self, model, **hints):
        return getattr(model, "_DATABASE", "default")

    def allow_relation(self, obj1, obj2, **hints):
        db_list = ('default')
        return obj1._state.db in db_list and obj2._state.db in db_list
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'default':
            return db == 'default'
        return None
        