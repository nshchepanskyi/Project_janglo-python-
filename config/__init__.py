"""Django project config.

PyMySQL замінює mysqlclient: чистий Python без системних залежностей,
тому працює і локально, і в збірковому середовищі Render.
"""
try:
    import pymysql

    # Django вимагає MySQLdb >= 2.2.1 (це mysqlclient); PyMySQL підставляє
    # себе під іменем MySQLdb, тому «повідомляємо» сумісну версію.
    pymysql.version_info = (2, 2, 3, 'final', 0)
    pymysql.install_as_MySQLdb()
except ImportError:
    # Локально на SQLite драйвер MySQL не потрібен.
    pass
