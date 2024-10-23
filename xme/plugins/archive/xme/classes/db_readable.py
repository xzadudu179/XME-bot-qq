from abc import ABC, abstractmethod
from functools import wraps

class DbReadable(ABC):
    """可被数据库读取类
    """
    def __init__(self, id, database) -> None:
        self.id = id
        self.database = database
        self.init_table()

    def update_data(func):
        """数据更新装饰函数

        Args:
            func (_type_): 装饰函数
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)  # 调用原始函数
            if not result:
                # 如果返回 False 等值不执行保存
                return result
            if type(result) == tuple:
                if not result[0]: return result
                # result = result[1]
            # 在函数执行完毕后执行的指令
            self.save()
            print("数据已更新.")
            return result
        return wrapper


    @abstractmethod
    def load_by_id(self, database, id, table_name):
        ...

    def save(self):
        """保存本类数据至数据库
        """
        self.database.save_to_db(self)

    def init_table(self):
        """初始化数据库表
        """
        self.database.create_table(self)