import lib_db as datab
import library
import search


def bootstrap():
    datab.init_conn()
    datab.setup_db()
    datab.user_conf()
    library.sync_library()
    search.init_cache()


def shutdown():
    datab.shut_conn()
