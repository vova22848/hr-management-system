import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any


class Database:
    def __init__(self, db_name="hr_arm.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Для доступа по именам колонок
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        # Подразделения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                manager_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Должности
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                base_salary REAL NOT NULL,
                department_id INTEGER,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            )
        ''')
        # Сотрудники
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                patronymic TEXT,
                birth_date DATE,
                gender TEXT CHECK(gender IN ('М', 'Ж')),
                passport TEXT,
                snils TEXT,
                inn TEXT,
                address TEXT,
                phone TEXT,
                email TEXT,
                hire_date DATE NOT NULL,
                fire_date DATE,
                position_id INTEGER,
                department_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE SET NULL,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            )
        ''')
        # Приказы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL,
                order_type TEXT CHECK(order_type IN ('прием', 'увольнение', 'перевод', 'отпуск', 'командировка', 'премия', 'взыскание')),
                description TEXT,
                employee_id INTEGER NOT NULL,
                order_date DATE NOT NULL,
                effective_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        ''')
        # Отпуска
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                vacation_type TEXT CHECK(vacation_type IN ('ежегодный', 'учебный', 'без сохранения', 'декретный', 'по уходу')),
                order_id INTEGER,
                approved BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
            )
        ''')
        # Командировки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                purpose TEXT,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
            )
        ''')
        # Больничные листы
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sick_leaves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                diagnosis TEXT,
                order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
            )
        ''')
        self.conn.commit()

        # Заполняем тестовыми данными, если база пустая
        cnt = self.cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        if cnt == 0:
            print("📦 База данных пуста. Загружаю тестовые данные...")
            self._insert_test_data()
            print("✅ Тестовые данные успешно загружены!")

    def _insert_test_data(self):
        """Заполнение базы тестовыми данными"""

        # 1. Подразделения
        print("  📁 Добавление подразделений...")
        departments_data = [
            ('Администрация', None),
            ('Отдел продаж', 5),
            ('IT-отдел', 8),
            ('Бухгалтерия', 12)
        ]
        for name, manager_id in departments_data:
            self.execute("INSERT INTO departments (name, manager_id) VALUES (?, ?)", (name, manager_id))

        # 2. Должности
        print("  💼 Добавление должностей...")
        positions_data = [
            ('Генеральный директор', 250000, 1),
            ('Коммерческий директор', 180000, 2),
            ('Менеджер по продажам', 80000, 2),
            ('Руководитель IT-отдела', 160000, 3),
            ('Старший разработчик', 140000, 3),
            ('Разработчик', 100000, 3),
            ('Главный бухгалтер', 150000, 4),
            ('Бухгалтер', 70000, 4)
        ]
        for title, salary, dept_id in positions_data:
            self.execute("""
                INSERT INTO positions (title, base_salary, department_id) 
                VALUES (?, ?, ?)
            """, (title, salary, dept_id))

        # 3. Сотрудники
        print("  👥 Добавление сотрудников...")
        employees_data = [
            # Администрация
            ('Алексей', 'Иванов', 'Петрович', '1980-05-15', 'М', '4510 123456', '123-456-789 01', '770123456789',
             'г. Москва, ул. Тверская, д. 1, кв. 10', '+7(999)123-45-67', 'a.ivanov@company.ru', '2020-01-10', 1, 1, 1),
            # Отдел продаж
            ('Елена', 'Смирнова', 'Александровна', '1985-08-22', 'Ж', '4511 234567', '234-567-890 12', '770234567890',
             'г. Москва, ул. Арбат, д. 5, кв. 22', '+7(999)234-56-78', 'e.smirnova@company.ru', '2021-03-15', 2, 2, 1),
            ('Дмитрий', 'Козлов', 'Игоревич', '1990-11-03', 'М', '4512 345678', '345-678-901 23', '770345678901',
             'г. Москва, ул. Ленина, д. 10, кв. 5', '+7(999)345-67-89', 'd.kozlov@company.ru', '2022-06-01', 3, 2, 1),
            ('Анна', 'Новикова', 'Сергеевна', '1995-02-14', 'Ж', '4513 456789', '456-789-012 34', '770456789012',
             'г. Москва, ул. Пушкина, д. 15, кв. 30', '+7(999)456-78-90', 'a.novikova@company.ru', '2023-01-20', 3, 2,
             1),
            ('Павел', 'Морозов', 'Викторович', '1988-09-30', 'М', '4514 567890', '567-890-123 45', '770567890123',
             'г. Москва, пр. Мира, д. 20, кв. 12', '+7(999)567-89-01', 'p.morozov@company.ru', '2021-09-10', 3, 2, 1),
            ('Марина', 'Волкова', 'Дмитриевна', '1992-07-18', 'Ж', '4515 678901', '678-901-234 56', '770678901234',
             'г. Москва, ул. Строителей, д. 7, кв. 45', '+7(999)678-90-12', 'm.volkova@company.ru', '2024-02-01', 3, 2,
             1),
            # IT-отдел
            ('Сергей', 'Петров', 'Андреевич', '1982-12-05', 'М', '4516 789012', '789-012-345 67', '770789012345',
             'г. Москва, ул. Гагарина, д. 25, кв. 8', '+7(999)789-01-23', 's.petrov@company.ru', '2020-05-20', 4, 3, 1),
            ('Андрей', 'Соколов', 'Владимирович', '1987-04-12', 'М', '4517 890123', '890-123-456 78', '770890123456',
             'г. Москва, ул. Королева, д. 30, кв. 17', '+7(999)890-12-34', 'a.sokolov@company.ru', '2021-11-01', 5, 3,
             1),
            ('Ольга', 'Лебедева', 'Николаевна', '1991-10-25', 'Ж', '4518 901234', '901-234-567 89', '770901234567',
             'г. Москва, ул. Космонавтов, д. 12, кв. 33', '+7(999)901-23-45', 'o.lebedeva@company.ru', '2022-08-15', 6,
             3, 1),
            ('Игорь', 'Виноградов', 'Алексеевич', '1998-03-08', 'М', '4519 012345', '012-345-678 90', '770012345678',
             'г. Москва, ул. Молодежная, д. 8, кв. 19', '+7(999)012-34-56', 'i.vinogradov@company.ru', '2023-04-10', 6,
             3, 1),
            ('Татьяна', 'Кузнецова', 'Ивановна', '1996-06-21', 'Ж', '4520 123450', '123-456-789 10', '770123456780',
             'г. Москва, ул. Садовая, д. 18, кв. 27', '+7(999)123-45-60', 't.kuznetsova@company.ru', '2024-01-15', 6, 3,
             1),
            # Бухгалтерия
            ('Наталья', 'Васильева', 'Петровна', '1975-01-30', 'Ж', '4521 234561', '234-567-890 21', '770234567891',
             'г. Москва, ул. Новая, д. 3, кв. 14', '+7(999)234-56-71', 'n.vasilieva@company.ru', '2019-09-01', 7, 4, 1),
            ('Екатерина', 'Попова', 'Сергеевна', '1989-08-17', 'Ж', '4522 345672', '345-678-901 32', '770345678902',
             'г. Москва, ул. Лесная, д. 11, кв. 9', '+7(999)345-67-82', 'e.popova@company.ru', '2022-03-10', 8, 4, 1),
            ('Галина', 'Зайцева', 'Александровна', '1993-11-05', 'Ж', '4523 456783', '456-789-012 43', '770456789013',
             'г. Москва, ул. Парковая, д. 6, кв. 41', '+7(999)456-78-93', 'g.zaytseva@company.ru', '2023-07-01', 8, 4,
             1),
            # Уволенный сотрудник
            ('Виктор', 'Степанов', 'Олегович', '1983-09-12', 'М', '4524 567894', '567-890-123 54', '770567890124',
             'г. Москва, ул. Речная, д. 4, кв. 2', '+7(999)567-89-04', 'v.stepanov@company.ru', '2021-02-15', 3, 2, 0)
        ]

        for emp in employees_data:
            self.execute("""
                INSERT INTO employees 
                (first_name, last_name, patronymic, birth_date, gender, passport, snils, inn, 
                 address, phone, email, hire_date, position_id, department_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, emp)

        # Обновим fire_date для уволенного сотрудника
        self.execute("UPDATE employees SET fire_date = ? WHERE id = ?", ('2023-12-20', 15))

        # 4. Приказы
        print("  📄 Добавление приказов...")
        orders_data = [
            ('ПР-20200110-001', 'прием', 'Прием на работу на должность Генерального директора', 1, '2020-01-10',
             '2020-01-10'),
            ('ПР-20210315-002', 'прием', 'Прием на работу на должность Коммерческого директора', 2, '2021-03-15',
             '2021-03-15'),
            ('ПР-20220601-003', 'прием', 'Прием на работу на должность Менеджера по продажам', 3, '2022-06-01',
             '2022-06-01'),
            ('ПР-20230120-004', 'прием', 'Прием на работу на должность Менеджера по продажам', 4, '2023-01-20',
             '2023-01-20'),
            ('ПР-20210910-005', 'прием', 'Прием на работу на должность Менеджера по продажам', 5, '2021-09-10',
             '2021-09-10'),
            ('ПР-20240201-006', 'прием', 'Прием на работу на должность Менеджера по продажам', 6, '2024-02-01',
             '2024-02-01'),
            ('ПР-20200520-007', 'прием', 'Прием на работу на должность Руководителя IT-отдела', 7, '2020-05-20',
             '2020-05-20'),
            ('ПР-20211101-008', 'прием', 'Прием на работу на должность Старшего разработчика', 8, '2021-11-01',
             '2021-11-01'),
            ('ПР-20220815-009', 'прием', 'Прием на работу на должность Разработчика', 9, '2022-08-15', '2022-08-15'),
            ('ПР-20230410-010', 'прием', 'Прием на работу на должность Разработчика', 10, '2023-04-10', '2023-04-10'),
            ('ПР-20240115-011', 'прием', 'Прием на работу на должность Разработчика', 11, '2024-01-15', '2024-01-15'),
            ('ПР-20190901-012', 'прием', 'Прием на работу на должность Главного бухгалтера', 12, '2019-09-01',
             '2019-09-01'),
            ('ПР-20220310-013', 'прием', 'Прием на работу на должность Бухгалтера', 13, '2022-03-10', '2022-03-10'),
            ('ПР-20230701-014', 'прием', 'Прием на работу на должность Бухгалтера', 14, '2023-07-01', '2023-07-01'),
            ('ПР-20210215-015', 'прием', 'Прием на работу на должность Менеджера по продажам', 15, '2021-02-15',
             '2021-02-15'),
            ('УВ-20231220-001', 'увольнение', 'Увольнение по собственному желанию', 15, '2023-12-20', '2023-12-20'),
            ('ПЕР-20230401-001', 'перевод', 'Перевод на должность Старшего разработчика', 9, '2023-04-01',
             '2023-04-01'),
            ('ПРМ-20240301-001', 'премия', 'Премия за успешное выполнение квартального плана', 2, '2024-03-01',
             '2024-03-01'),
            ('ПРМ-20240301-002', 'премия', 'Премия за внедрение новой CRM системы', 7, '2024-03-01', '2024-03-01')
        ]

        for order in orders_data:
            self.execute("""
                INSERT INTO orders (order_number, order_type, description, employee_id, order_date, effective_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, order)

        # 5. Отпуска
        print("  🏖️ Добавление отпусков...")
        vacations_data = [
            (1, '2024-07-01', '2024-07-14', 'ежегодный', 1),
            (2, '2024-06-10', '2024-06-24', 'ежегодный', 1),
            (3, '2024-08-05', '2024-08-18', 'ежегодный', 1),
            (4, '2024-05-20', '2024-06-02', 'ежегодный', 1),
            (7, '2024-09-01', '2024-09-14', 'ежегодный', 1),
            (8, '2024-04-15', '2024-04-28', 'ежегодный', 1),
            (12, '2024-07-15', '2024-07-28', 'ежегодный', 1),
            (13, '2024-03-10', '2024-03-24', 'учебный', 1),
            (14, '2024-11-01', '2025-02-01', 'декретный', 1)
        ]

        for vac in vacations_data:
            self.execute("""
                INSERT INTO vacations (employee_id, start_date, end_date, vacation_type, approved)
                VALUES (?, ?, ?, ?, ?)
            """, vac)

        # 6. Командировки
        print("  ✈️ Добавление командировок...")
        trips_data = [
            (2, 'г. Санкт-Петербург', 'Переговоры с партнерами', '2024-04-10', '2024-04-12'),
            (3, 'г. Казань', 'Участие в выставке', '2024-05-15', '2024-05-17'),
            (7, 'г. Новосибирск', 'Внедрение ПО у клиента', '2024-03-20', '2024-03-22'),
            (8, 'г. Екатеринбург', 'Технический аудит', '2024-06-05', '2024-06-07')
        ]

        for trip in trips_data:
            self.execute("""
                INSERT INTO business_trips (employee_id, destination, purpose, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
            """, trip)

        # 7. Больничные листы
        print("  🏥 Добавление больничных листов...")
        sick_leaves_data = [
            (5, '2024-02-10', '2024-02-17', 'ОРВИ'),
            (11, '2024-03-01', '2024-03-05', 'Грипп'),
            (13, '2024-01-15', '2024-01-22', 'Бронхит')
        ]

        for sick in sick_leaves_data:
            self.execute("""
                INSERT INTO sick_leaves (employee_id, start_date, end_date, diagnosis)
                VALUES (?, ?, ?, ?)
            """, sick)

        print("  ✅ Тестовые данные загружены:")
        print(f"     • Подразделений: {len(departments_data)}")
        print(f"     • Должностей: {len(positions_data)}")
        print(f"     • Сотрудников: {len(employees_data)}")
        print(f"     • Приказов: {len(orders_data)}")
        print(f"     • Отпусков: {len(vacations_data)}")
        print(f"     • Командировок: {len(trips_data)}")
        print(f"     • Больничных: {len(sick_leaves_data)}")

    def execute(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

    def fetch_all(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]

    def fetch_one(self, query: str, params: tuple = ()):
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()