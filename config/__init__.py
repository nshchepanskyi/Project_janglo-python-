"""Django project config.

PyMySQL замінює mysqlclient: чистий Python без системних залежностей,
тому працює і локально, і в збірковому середовищі Render.
"""
try:
    import pymysql



    pymysql.version_info = (2, 2, 3, 'final', 0)
    pymysql.install_as_MySQLdb()
except ImportError:

    pass
